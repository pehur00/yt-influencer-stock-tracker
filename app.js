let stockData = [];

const weights = {
  valueRank: 0.25,
  expectedReturn: 0.2,
  fcfQuality: 0.15,
  roicStrength: 0.15,
  balanceSheetStrength: 0.1,
  revenueDurability: 0.1,
  insiderActivity: 0.05,
};

// Free API endpoints for live prices
const FREE_PRICE_ENDPOINTS = [
  {
    name: 'Finnhub',
    url: 'https://finnhub.io/api/v1/quote?symbol=',
    transform: (data) => data.c, // current price
    key: 'cggo519r01qqr8lanv60cggo519r01qqr8lanv6g' // Replace with your free key
  },
  {
    name: 'Google Finance (Proxy)',
    url: 'https://www.google.com/finance/quote/',
    transform: null, // Requires custom parsing
    key: null
  }
];

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

let tableBody;
let sortSelect;
let sourceFilter;
let expandedStockKey = null;  // ticker|source unique key
let modalEl;
let modalContentEl;
let modalCloseEl;
let modalBackdropEl;
let livePriceStore = {};
let currentSortKey = 'undervaluationScore';
let currentSourceFilter = 'all';

function toHundredScale(score) {
  return score * 20;
}

function computeUndervaluationScore(stock) {
  const total =
    weights.valueRank * toHundredScale(stock.valueRank) +
    weights.expectedReturn * toHundredScale(stock.expectedReturn) +
    weights.fcfQuality * toHundredScale(stock.fcfQuality) +
    weights.roicStrength * toHundredScale(stock.roicStrength) +
    weights.balanceSheetStrength * toHundredScale(stock.balanceSheetStrength) +
    weights.revenueDurability * toHundredScale(stock.revenueDurability) +
    weights.insiderActivity * toHundredScale(stock.insiderActivity);

  return Math.round(total);
}

function deriveRiskLevel(stock) {
  const avgQuality =
    (stock.fcfQuality + stock.roicStrength + stock.revenueDurability + stock.balanceSheetStrength) / 4;

  if (avgQuality >= 4.3) return 'Low';
  if (avgQuality >= 3.3) return 'Moderate';
  if (avgQuality >= 2.5) return 'High';
  return 'Speculative';
}

function deriveQualitySummary(stock) {
  return ((stock.fcfQuality + stock.roicStrength) / 2).toFixed(1);
}

function getLivePrice(ticker) {
  const key = ticker.toUpperCase();
  const value = livePriceStore[key];
  return typeof value === 'number' ? value : null;
}

function computePnlPercentage(initialPrice, livePrice) {
  if (typeof initialPrice !== 'number' || typeof livePrice !== 'number' || initialPrice === 0) {
    return null;
  }
  return ((livePrice - initialPrice) / initialPrice) * 100;
}

function formatCurrency(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '—';
  }
  return currencyFormatter.format(value);
}

function formatPnL(pnlPercent) {
  if (typeof pnlPercent !== 'number' || Number.isNaN(pnlPercent)) {
    return '—';
  }
  const rounded = pnlPercent.toFixed(2);
  return `${pnlPercent > 0 ? '+' : ''}${rounded}%`;
}

function pnlClassName(pnlPercent) {
  if (typeof pnlPercent !== 'number' || Number.isNaN(pnlPercent)) return '';
  return pnlPercent >= 0 ? 'pnl-positive' : 'pnl-negative';
}

function normalizeNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function deriveModels(stock) {
  const automationPrice = normalizeNumber(stock.price);
  const initialPriceSource = normalizeNumber(stock.initialPrice);
  const initialPrice =
    typeof initialPriceSource === 'number' ? initialPriceSource : normalizeNumber(stock.price ?? automationPrice);
  const livePrice = normalizeNumber(getLivePrice(stock.ticker));
  const pnlPercent = computePnlPercentage(initialPrice, livePrice);

  return {
    ...stock,
    price: automationPrice,
    initialPrice,
    livePrice,
    pnlPercent,
    undervaluationScore: computeUndervaluationScore(stock),
    riskLevel: deriveRiskLevel(stock),
    qualitySummary: deriveQualitySummary(stock),
  };
}

function renderTable(sortKey = currentSortKey) {
  currentSortKey = sortKey;
  expandedStockKey = null;
  let viewModels = stockData.map(deriveModels);
  
  // Apply source filter
  if (currentSourceFilter !== 'all') {
    viewModels = viewModels.filter(stock => stock.source === currentSourceFilter);
  }
  
  viewModels.sort((a, b) => {
    const dir = sortKey === 'price' ? 1 : -1; // price is ascending, scores descending
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal === bVal) {
      return a.ticker.localeCompare(b.ticker);
    }
    return dir * (aVal - bVal);
  });

  tableBody.innerHTML = '';
  viewModels.forEach((stock) => {
    const row = document.createElement('tr');
    row.classList.add('data-row');
    // Use ticker + source as unique key
    const stockKey = `${stock.ticker}|${stock.source || 'Unknown'}`;
    row.dataset.stockKey = stockKey;

    row.innerHTML = `
      <td><span class="badge category-${stock.category.toLowerCase()}">${stock.category}</span></td>
      <td>${stock.ticker}</td>
      <td>${stock.name}</td>
      <td><span class="badge source">${stock.source || 'Unknown'}</span></td>
      <td>${stock.recommendedDate || '-'}</td>
      <td>${formatCurrency(stock.initialPrice)}</td>
      <td>${formatCurrency(stock.livePrice)}</td>
      <td class="${pnlClassName(stock.pnlPercent)}">${formatPnL(stock.pnlPercent)}</td>
      <td><span class="badge value">${stock.dcf.base}</span></td>
      <td>${stock.valueRank.toFixed(1)}</td>
      <td>${stock.qualitySummary}</td>
      <td>${stock.undervaluationScore}</td>
      <td>${renderRiskBadge(stock.riskLevel)}</td>
      <td>${stock.lastUpdated}</td>
    `;

    row.addEventListener('click', () => toggleDetailRow(stock, row));
    tableBody.appendChild(row);

    if (expandedStockKey === stockKey) {
      appendDetailRow(stock, row);
    }
  });
}

function renderRiskBadge(riskLevel) {
  const key = riskLevel.toLowerCase();
  return `<span class="badge risk-${key}">${riskLevel}</span>`;
}

function toggleDetailRow(stock, row) {
  const stockKey = `${stock.ticker}|${stock.source || 'Unknown'}`;
  const alreadyExpanded = expandedStockKey === stockKey;
  collapseDetailRow();

  if (!alreadyExpanded) {
    expandedStockKey = stockKey;
    appendDetailRow(stock, row);
  }
}

function collapseDetailRow() {
  const detailRow = tableBody.querySelector('tr.detail-row');
  if (detailRow) {
    detailRow.remove();
  }
  expandedStockKey = null;
}

function appendDetailRow(stock, row) {
  const detailRow = document.createElement('tr');
  detailRow.classList.add('detail-row');
  const colSpan = document.querySelectorAll('#stock-table thead th').length;
  detailRow.innerHTML = `<td colspan="${colSpan}">${buildDetailCard(stock)}</td>`;
  row.insertAdjacentElement('afterend', detailRow);

  const explainBtn = detailRow.querySelector('.explain-btn');
  if (explainBtn) {
    explainBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      openExplanationModal(stock);
    });
  }
}

function buildDetailCard(stock) {
  const factors = [
    ['Source', stock.source || 'Unknown'],
    ['Automation Price', formatCurrency(stock.price)],
    ['Initial Price', formatCurrency(stock.initialPrice)],
    ['Live Price', formatCurrency(stock.livePrice)],
    ['PnL %', formatPnL(stock.pnlPercent)],
    ['DCF Conservative', stock.dcf.conservative],
    ['DCF Base', stock.dcf.base],
    ['DCF Aggressive', stock.dcf.aggressive],
    ['FCF Quality', stock.fcfQuality],
    ['ROIC Strength', stock.roicStrength],
    ['Revenue Durability', stock.revenueDurability],
    ['Balance Sheet Strength', stock.balanceSheetStrength],
    ['Insider Activity', stock.insiderActivity],
    ['Value Rank', stock.valueRank],
    ['Expected Return', stock.expectedReturn],
  ];

  const recommendedDate = stock.recommendedDate || 'N/A';

  return `
    <div class="detail-card">
      <h4>${stock.name} (${stock.ticker})</h4>
      <div class="factor">
        <span class="label">Source</span>
        <span class="value">${stock.source || 'Unknown'}</span>
      </div>
      <div class="factor">
        <span class="label">Recommended Date</span>
        <span class="value">${recommendedDate}</span>
      </div>
      ${factors
        .map(
          ([label, value]) => `
            <div class="factor">
              <span class="label">${label}</span>
              <span class="value">${value}</span>
            </div>
          `,
        )
        .join('')}
      <div class="factor">
        <span class="label">Undervaluation Score</span>
        <span class="value">${stock.undervaluationScore}</span>
      </div>
      <div class="factor">
        <span class="label">Risk Level</span>
        <span class="value">${stock.riskLevel}</span>
      </div>
      <div class="factor">
        <span class="label">Last Updated</span>
        <span class="value">${stock.lastUpdated}</span>
      </div>
      <div class="explanations">
        <button type="button" class="explain-btn">View Column Explanations</button>
      </div>
    </div>
  `;
}

async function fetchStockData() {
  try {
    const response = await fetch('data/stocks.json');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    stockData = await response.json();
    return true;
  } catch (error) {
    console.error('Failed to load stock data:', error);
    return false;
  }
}

function showError() {
  tableBody = document.querySelector('#stock-table tbody');
  if (!tableBody) return;

  tableBody.innerHTML = `
    <tr>
      <td colspan="14" style="text-align: center; padding: 2rem; color: hsl(var(--muted-foreground));">
        Failed to load stock data. Please try refreshing the page.
      </td>
    </tr>
  `;
}

function showLoading() {
  tableBody = document.querySelector('#stock-table tbody');
  if (!tableBody) return;

  tableBody.innerHTML = `
    <tr>
      <td colspan="14" style="text-align: center; padding: 2rem; color: hsl(var(--muted-foreground));">
        Loading stock data...
      </td>
    </tr>
  `;
}

async function initUndervaluationTable() {
  tableBody = document.querySelector('#stock-table tbody');
  sortSelect = document.querySelector('#sort-select');
  sourceFilter = document.querySelector('#source-filter');
  modalEl = document.getElementById('explanation-modal');
  modalContentEl = modalEl?.querySelector('.modal__content') || null;
  modalCloseEl = modalEl?.querySelector('.modal__close') || null;
  modalBackdropEl = modalEl?.querySelector('.modal__backdrop') || null;

  modalCloseEl?.addEventListener('click', closeExplanationModal);
  modalBackdropEl?.addEventListener('click', closeExplanationModal);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeExplanationModal();
    }
  });

  if (!tableBody || !sortSelect) return;

  showLoading();

  const success = await fetchStockData();
  if (!success) {
    showError();
    return;
  }

  // Populate source filter dropdown
  if (sourceFilter) {
    const sources = [...new Set(stockData.map(s => s.source || 'Unknown'))].sort();
    sources.forEach(source => {
      const option = document.createElement('option');
      option.value = source;
      option.textContent = source;
      sourceFilter.appendChild(option);
    });
    
    sourceFilter.addEventListener('change', (event) => {
      currentSourceFilter = event.target.value;
      renderTable();
    });
  }

  sortSelect.addEventListener('change', (event) => {
    const sortKey = event.target.value;
    renderTable(sortKey);
  });

  renderTable();
  renderChannelStats();
  refreshLivePrices(stockData);

  // Initialize YouTube modal
  initYouTubeModal();
}

// Channel Performance Stats
function calculateChannelStats() {
  const channelMap = {};
  
  stockData.forEach(stock => {
    const source = stock.source || 'Unknown';
    if (!channelMap[source]) {
      channelMap[source] = {
        name: source,
        stocks: [],
        totalPnl: 0,
        avgPnl: 0,
        winners: 0,
        losers: 0,
        totalStocks: 0,
        avgScore: 0,
        avgQuality: 0,
        categories: { Dividend: 0, Growth: 0 }
      };
    }
    
    const model = deriveModels(stock);
    channelMap[source].stocks.push(model);
    channelMap[source].totalStocks++;
    channelMap[source].categories[stock.category] = (channelMap[source].categories[stock.category] || 0) + 1;
    
    if (typeof model.pnlPercent === 'number' && !isNaN(model.pnlPercent)) {
      channelMap[source].totalPnl += model.pnlPercent;
      if (model.pnlPercent >= 0) {
        channelMap[source].winners++;
      } else {
        channelMap[source].losers++;
      }
    }
    
    channelMap[source].avgScore += model.undervaluationScore;
    channelMap[source].avgQuality += parseFloat(model.qualitySummary) || 0;
  });
  
  // Calculate averages
  Object.values(channelMap).forEach(channel => {
    if (channel.totalStocks > 0) {
      channel.avgPnl = channel.totalPnl / channel.totalStocks;
      channel.avgScore = Math.round(channel.avgScore / channel.totalStocks);
      channel.avgQuality = (channel.avgQuality / channel.totalStocks).toFixed(1);
      channel.winRate = channel.totalStocks > 0 
        ? Math.round((channel.winners / channel.totalStocks) * 100) 
        : 0;
    }
  });
  
  return Object.values(channelMap).sort((a, b) => b.avgPnl - a.avgPnl);
}

function renderChannelStatsCard(channel) {
  const pnlClass = channel.avgPnl >= 0 ? 'pnl-positive' : 'pnl-negative';
  const pnlSign = channel.avgPnl >= 0 ? '+' : '';
  
  return `
    <div class="channel-stat-card">
      <div class="channel-stat-card__header">
        <span class="badge source">${channel.name}</span>
        <span class="channel-stat-card__pnl ${pnlClass}">${pnlSign}${channel.avgPnl.toFixed(2)}%</span>
      </div>
      <div class="channel-stat-card__stats">
        <div class="channel-stat-card__stat">
          <span class="channel-stat-card__label">Stocks</span>
          <span class="channel-stat-card__value">${channel.totalStocks}</span>
        </div>
        <div class="channel-stat-card__stat">
          <span class="channel-stat-card__label">Win Rate</span>
          <span class="channel-stat-card__value">${channel.winRate}%</span>
        </div>
        <div class="channel-stat-card__stat">
          <span class="channel-stat-card__label">Avg Score</span>
          <span class="channel-stat-card__value">${channel.avgScore}</span>
        </div>
        <div class="channel-stat-card__stat">
          <span class="channel-stat-card__label">Quality</span>
          <span class="channel-stat-card__value">${channel.avgQuality}</span>
        </div>
      </div>
      <div class="channel-stat-card__breakdown">
        <span class="badge category-dividend">${channel.categories.Dividend || 0} Div</span>
        <span class="badge category-growth">${channel.categories.Growth || 0} Growth</span>
        <span class="channel-stat-card__record">${channel.winners}W / ${channel.losers}L</span>
      </div>
    </div>
  `;
}

function renderChannelStats() {
  const container = document.getElementById('channel-stats-container');
  if (!container) return;
  
  const stats = calculateChannelStats();
  
  if (stats.length === 0) {
    container.innerHTML = '<p class="text-sm text-muted-foreground">No channel data available yet.</p>';
    return;
  }
  
  container.innerHTML = stats.map(renderChannelStatsCard).join('');
}

// YouTube Modal Functionality
let youtubeModalEl;
let youtubeVideosContainer;
let youtubeVideosData = [];

async function fetchYouTubeVideos() {
  try {
    const response = await fetch('data/youtube_videos.json');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    youtubeVideosData = await response.json();
    return true;
  } catch (error) {
    console.warn('Could not load YouTube videos data:', error);
    return false;
  }
}

function renderYouTubeVideoCard(video, index) {
  const allTickers = [
    ...(video.tickersBought || []),
    ...(video.tickersRecommended || []),
    ...(video.tickersMentioned || [])
  ];
  const uniqueTickers = [...new Set(allTickers)];
  const tickerSummary = uniqueTickers.length > 0 
    ? uniqueTickers.slice(0, 5).join(', ') + (uniqueTickers.length > 5 ? '...' : '')
    : 'No tickers';

  const tickersBoughtHtml = video.tickersBought?.length
    ? `<div class="youtube-video-card__tickers-section">
        <span class="youtube-video-card__tickers-label">Bought:</span>
        ${video.tickersBought.map(t => `<span class="ticker-badge bought">${t}</span>`).join('')}
      </div>`
    : '';

  const tickersRecommendedHtml = video.tickersRecommended?.length
    ? `<div class="youtube-video-card__tickers-section">
        <span class="youtube-video-card__tickers-label">Recommended:</span>
        ${video.tickersRecommended.map(t => `<span class="ticker-badge recommended">${t}</span>`).join('')}
      </div>`
    : '';

  const tickersMentionedHtml = video.tickersMentioned?.length
    ? `<div class="youtube-video-card__tickers-section">
        <span class="youtube-video-card__tickers-label">Mentioned:</span>
        ${video.tickersMentioned.map(t => `<span class="ticker-badge">${t}</span>`).join('')}
      </div>`
    : '';

  const insightsHtml = video.keyInsights?.length
    ? `<div class="youtube-video-card__insights">
        <p class="youtube-video-card__insights-title">Key Insights</p>
        <ul class="youtube-video-card__insights-list">
          ${video.keyInsights.map(insight => `<li>${insight}</li>`).join('')}
        </ul>
      </div>`
    : '';

  const thumbnailHtml = video.thumbnail && !video.thumbnail.includes('example')
    ? `<img src="${video.thumbnail}" alt="${video.title}" onerror="this.parentElement.innerHTML='<div class=\\'youtube-video-card__thumbnail-placeholder\\'><svg viewBox=\\'0 0 24 24\\' fill=\\'currentColor\\'><path d=\\'M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z\\'/></svg></div>'">`
    : `<div class="youtube-video-card__thumbnail-placeholder">
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
        </svg>
      </div>`;

  const videoUrl = `https://www.youtube.com/watch?v=${video.videoId}`;
  const channelName = video.channelName || 'Unknown Channel';

  return `
    <article class="youtube-video-row" data-video-id="${video.videoId}">
      <div class="youtube-video-row__header" onclick="toggleVideoDetails('${video.videoId}')">
        <span class="youtube-video-row__expand-icon">▶</span>
        <span class="youtube-video-row__channel badge source">${channelName}</span>
        <span class="youtube-video-row__title">${video.title}</span>
        <span class="youtube-video-row__tickers">${tickerSummary}</span>
        <span class="youtube-video-row__date">${video.publishedAt}</span>
      </div>
      <div class="youtube-video-row__details" id="video-details-${video.videoId}">
        <div class="youtube-video-card__expanded">
          <a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="youtube-video-card__thumbnail-link">
            <div class="youtube-video-card__thumbnail">
              ${thumbnailHtml}
              <div class="youtube-video-card__play-overlay">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </div>
            </div>
          </a>
          <div class="youtube-video-card__content">
            <p class="youtube-video-card__summary">${video.summary}</p>
            <div class="youtube-video-card__tickers">
              ${tickersBoughtHtml}
              ${tickersRecommendedHtml}
              ${tickersMentionedHtml}
            </div>
            ${insightsHtml}
            <a href="${videoUrl}" target="_blank" rel="noopener noreferrer" class="youtube-video-card__watch-btn">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              Watch on YouTube
            </a>
          </div>
        </div>
      </div>
    </article>
  `;
}

// Toggle video details expansion
function toggleVideoDetails(videoId) {
  const details = document.getElementById(`video-details-${videoId}`);
  const row = details?.closest('.youtube-video-row');
  if (!details || !row) return;
  
  const isExpanded = row.classList.contains('expanded');
  
  // Collapse all others first
  document.querySelectorAll('.youtube-video-row.expanded').forEach(el => {
    el.classList.remove('expanded');
  });
  
  // Toggle this one
  if (!isExpanded) {
    row.classList.add('expanded');
  }
}

function renderYouTubeVideos() {
  if (!youtubeVideosContainer) return;

  // Filter videos based on current source filter
  let filteredVideos = youtubeVideosData;
  if (currentSourceFilter !== 'all') {
    filteredVideos = youtubeVideosData.filter(v => v.channelName === currentSourceFilter);
  }

  if (!filteredVideos.length) {
    const filterMsg = currentSourceFilter !== 'all' 
      ? `<p style="font-size: 0.85rem; margin-top: 0.5rem;">No videos from "${currentSourceFilter}". Try selecting "All Channels" in the filter.</p>`
      : `<p style="font-size: 0.85rem; margin-top: 0.5rem;">Run the automation crew to fetch the latest videos from YouTube finance channels.</p>`;
    
    youtubeVideosContainer.innerHTML = `
      <div class="youtube-error">
        <p>No video data available.</p>
        ${filterMsg}
      </div>
    `;
    return;
  }

  youtubeVideosContainer.innerHTML = filteredVideos
    .map((video, index) => renderYouTubeVideoCard(video, index))
    .join('');
}

function openYouTubeModal() {
  if (!youtubeModalEl) return;
  renderYouTubeVideos();
  youtubeModalEl.classList.remove('hidden');
}

function closeYouTubeModal() {
  if (!youtubeModalEl) return;
  youtubeModalEl.classList.add('hidden');
}

async function initYouTubeModal() {
  youtubeModalEl = document.getElementById('youtube-modal');
  youtubeVideosContainer = document.getElementById('youtube-videos-container');

  const youtubeBtn = document.getElementById('youtube-videos-btn');
  const youtubeCloseBtn = youtubeModalEl?.querySelector('.modal__close');
  const youtubeBackdrop = youtubeModalEl?.querySelector('.modal__backdrop');

  youtubeBtn?.addEventListener('click', openYouTubeModal);
  youtubeCloseBtn?.addEventListener('click', closeYouTubeModal);
  youtubeBackdrop?.addEventListener('click', closeYouTubeModal);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && youtubeModalEl && !youtubeModalEl.classList.contains('hidden')) {
      closeYouTubeModal();
    }
  });

  // Pre-fetch YouTube videos data
  await fetchYouTubeVideos();
}

window.addEventListener('DOMContentLoaded', initUndervaluationTable);

function openExplanationModal(stock) {
  if (!modalEl || !modalContentEl) return;

  const analysis = stock.analysis || {};
  const priceNarrative =
    analysis.price ||
    `Latest price fetched from Yahoo Finance during the automation run: ${currencyFormatter.format(
      stock.price,
    )}.`;

  const dcfNarrative = (scenarioKey, label) => {
    const scenarioInfo =
      analysis.dcf?.[scenarioKey]?.narrative ||
      analysis.dcf?.[scenarioKey] ||
      'Scenario derived from the analyst agent using the fetched fundamentals.';
    const range = stock.dcf[scenarioKey];
    return `<li><strong>${label} (${range})</strong><p>${scenarioInfo}</p></li>`;
  };

  const scoreNarrative = (key, defaultText) => analysis.scores?.[key] || defaultText;

  const qualityInputs = [
    stock.fcfQuality,
    stock.roicStrength,
    stock.revenueDurability,
    stock.balanceSheetStrength,
  ];
  const avgQuality = (qualityInputs.reduce((sum, value) => sum + value, 0) / qualityInputs.length).toFixed(2);

  const contributions = [
    ['Value Rank', stock.valueRank, weights.valueRank, 'valueRank'],
    ['Expected Return', stock.expectedReturn, weights.expectedReturn, 'expectedReturn'],
    ['FCF Quality', stock.fcfQuality, weights.fcfQuality, 'fcfQuality'],
    ['ROIC Strength', stock.roicStrength, weights.roicStrength, 'roicStrength'],
    ['Balance Sheet Strength', stock.balanceSheetStrength, weights.balanceSheetStrength, 'balanceSheetStrength'],
    ['Revenue Durability', stock.revenueDurability, weights.revenueDurability, 'revenueDurability'],
    ['Insider Activity', stock.insiderActivity, weights.insiderActivity, 'insiderActivity'],
  ];

  const contributionList = contributions
    .map(([label, value, weight, key]) => {
      const weightPct = Math.round(weight * 100);
      const points = (toHundredScale(value) * weight).toFixed(1);
      const extra = analysis.scores?.[key] ? ` — ${analysis.scores[key]}` : '';
      return `<li><strong>${label}</strong>: score ${value} × weight ${weightPct}% = ${points} pts${extra}</li>`;
    })
    .join('');

  modalContentEl.innerHTML = `
    <h3>${stock.name} (${stock.ticker})</h3>
    <section>
      <h4>Price</h4>
      <p>${priceNarrative}</p>
    </section>
    <section>
      <h4>DCF Ranges</h4>
      <p>Per-share intrinsic value scenarios (constrained to ±200% of the fetched price unless explicitly justified).</p>
      <ul>
        ${dcfNarrative('conservative', 'Conservative')}
        ${dcfNarrative('base', 'Base')}
        ${dcfNarrative('aggressive', 'Aggressive')}
      </ul>
    </section>
    <section>
      <h4>Value Rank</h4>
      <p>${scoreNarrative('valueRank', 'LLM rating of relative cheapness versus intrinsic value.')}</p>
    </section>
    <section>
      <h4>Quality (FCF + ROIC)</h4>
      <p>${scoreNarrative(
        'quality',
        `Average of FCF Quality (${stock.fcfQuality}) and ROIC Strength (${stock.roicStrength}) = ${deriveQualitySummary(
          stock,
        )}.`,
      )}</p>
    </section>
    <section>
      <h4>Undervaluation Score</h4>
      <p>${analysis.undervaluation || 'Weighted blend of every factor, max 100.'}</p>
      <ul>${contributionList}</ul>
      <p>Total: <strong>${stock.undervaluationScore}</strong> points.</p>
    </section>
    <section>
      <h4>Risk Level</h4>
      <p>${analysis.risk || `Average quality (${avgQuality}) mapped to ${stock.riskLevel}.`}</p>
    </section>
    <section>
      <h4>Last Updated</h4>
      <p>${analysis.lastUpdated || `Automation run date: ${stock.lastUpdated}.`}</p>
    </section>
  `;

  modalEl.classList.remove('hidden');
}

function closeExplanationModal() {
  if (!modalEl) return;
  modalEl.classList.add('hidden');
}

async function refreshLivePrices(stocks) {
  const fallbackMap = stocks.reduce((acc, stock) => {
    const ticker = stock.ticker?.toUpperCase();
    const automationPrice = normalizeNumber(stock.price);
    if (ticker && typeof automationPrice === 'number') {
      acc[ticker] = automationPrice;
    }
    return acc;
  }, {});
  const uniqueTickers = Object.keys(fallbackMap);
  if (!uniqueTickers.length) return;

  // Attempt to fetch prices from multiple sources
  for (const endpoint of FREE_PRICE_ENDPOINTS) {
    try {
      const chunkSize = 4;
      for (let i = 0; i < uniqueTickers.length; i += chunkSize) {
        const chunk = uniqueTickers.slice(i, i + chunkSize);

        // Special handling for different endpoints
        if (endpoint.name === 'Finnhub') {
          const pricePromises = chunk.map(async (ticker) => {
            const url = `${endpoint.url}${ticker}&token=${endpoint.key}`;
            const response = await fetch(url);
            const data = await response.json();
            return { ticker, price: endpoint.transform(data) };
          });

          const results = await Promise.allSettled(pricePromises);
          results.forEach((result) => {
            if (result.status === 'fulfilled' && result.value.price) {
              livePriceStore[result.value.ticker] = result.value.price;
            }
          });
        }

        // Add more endpoint-specific logic here
      }

      // If we've successfully fetched some prices, break the loop
      if (Object.keys(livePriceStore).length > 0) {
        console.log(`✓ Fetched ${Object.keys(livePriceStore).length} live prices from ${endpoint.name}`);
        break;
      }
    } catch (error) {
      console.warn(`Failed to fetch live prices from ${endpoint.name}:`, error);
    }
  }

  // Fallback to automation prices if no live prices found
  uniqueTickers.forEach((ticker) => {
    if (!livePriceStore[ticker]) {
      const fallback = fallbackMap[ticker];
      if (typeof fallback === 'number') {
        livePriceStore[ticker] = fallback;
        console.log(`Using fallback price for ${ticker}: $${fallback}`);
      }
    }
  });

  // Update last fetched timestamp
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  const priceHeader = document.getElementById('live-price-header');
  if (priceHeader) {
    priceHeader.innerHTML = `Live Price <span style="font-size:0.6rem;opacity:0.7">(${timeStr})</span>`;
  }

  renderTable();
  renderChannelStats();
}
