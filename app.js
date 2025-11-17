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
let expandedTicker = null;
let modalEl;
let modalContentEl;
let modalCloseEl;
let modalBackdropEl;
let livePriceStore = {};
let currentSortKey = 'undervaluationScore';

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
  expandedTicker = null;
  const viewModels = stockData.map(deriveModels);
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
    row.dataset.ticker = stock.ticker;

    row.innerHTML = `
      <td><span class="badge category-${stock.category.toLowerCase()}">${stock.category}</span></td>
      <td>${stock.ticker}</td>
      <td>${stock.name}</td>
      <td>${formatCurrency(stock.price)}</td>
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

    if (expandedTicker === stock.ticker) {
      appendDetailRow(stock, row);
    }
  });
}

function renderRiskBadge(riskLevel) {
  const key = riskLevel.toLowerCase();
  return `<span class="badge risk-${key}">${riskLevel}</span>`;
}

function toggleDetailRow(stock, row) {
  const alreadyExpanded = expandedTicker === stock.ticker;
  collapseDetailRow();

  if (!alreadyExpanded) {
    expandedTicker = stock.ticker;
    appendDetailRow(stock, row);
  }
}

function collapseDetailRow() {
  const detailRow = tableBody.querySelector('tr.detail-row');
  if (detailRow) {
    detailRow.remove();
  }
  expandedTicker = null;
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

  return `
    <div class="detail-card">
      <h4>${stock.name} (${stock.ticker})</h4>
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
      <td colspan="13" style="text-align: center; padding: 2rem; color: hsl(var(--muted-foreground));">
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
      <td colspan="13" style="text-align: center; padding: 2rem; color: hsl(var(--muted-foreground));">
        Loading stock data...
      </td>
    </tr>
  `;
}

async function initUndervaluationTable() {
  tableBody = document.querySelector('#stock-table tbody');
  sortSelect = document.querySelector('#sort-select');
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

  sortSelect.addEventListener('change', (event) => {
    const sortKey = event.target.value;
    renderTable(sortKey);
  });

  renderTable();
  refreshLivePrices(stockData);
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
      }
    }
  });

  renderTable();
}
