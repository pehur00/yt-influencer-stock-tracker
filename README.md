# YouTube Influencer Stock Tracker

Track stock picks from top YouTube finance influencers. Aggregate recommendations, analyze valuations, and discover what the experts are buying.

## Features

- **Multi-Channel Support**: Track stocks from multiple YouTube finance channels
- **Automated Analysis**: CrewAI-powered stock analysis with DCF valuations
- **Live Prices**: Real-time price updates from Yahoo Finance
- **Channel Performance**: PnL tracking and win rate stats per channel
- **Collapsible Video List**: Browse latest videos with ticker summaries

## Valuation Methodology

### DCF (Discounted Cash Flow) Calculation

The AI analyst agent calculates intrinsic value using a standard DCF model with three scenarios:

```
Intrinsic Value = Σ (FCFₜ / (1 + r)ᵗ) + Terminal Value / (1 + r)ⁿ

Where:
  FCFₜ     = Free Cash Flow in year t
  r        = Discount rate (WACC)
  n        = Projection period (typically 10 years)
  Terminal = FCFₙ × (1 + g) / (r - g)  [Gordon Growth Model]
  g        = Terminal growth rate
```

**Three Scenarios:**

| Scenario | Revenue Growth | FCF Margin | Discount Rate | Terminal Growth |
|----------|---------------|------------|---------------|-----------------|
| **Conservative** | Low end of guidance | Compressed margins | Higher WACC (~10-12%) | 2% |
| **Base** | Consensus estimates | Stable margins | Market WACC (~8-10%) | 2.5% |
| **Aggressive** | Management targets | Margin expansion | Lower WACC (~7-9%) | 3% |

### Undervaluation Score (0-100)

A weighted composite score indicating how attractive a stock is on a risk-adjusted basis:

```
Score = Σ (Factor Score × Weight × 20)

Weights:
  Value Rank           25%   ← How cheap vs intrinsic value
  Expected Return      20%   ← Projected IRR based on DCF
  FCF Quality          15%   ← Free cash flow consistency & conversion
  ROIC Strength        15%   ← Return on invested capital vs WACC
  Balance Sheet        10%   ← Debt levels, liquidity, coverage
  Revenue Durability   10%   ← Recurring revenue, customer retention
  Insider Activity      5%   ← Recent insider buying/selling
```

Each factor is scored 1-5:
- **5** = Excellent (top quintile)
- **4** = Good (above average)
- **3** = Average
- **2** = Below average
- **1** = Poor (bottom quintile)

### Risk Level

Derived from average quality factors:

| Avg Quality | Risk Level |
|-------------|------------|
| ≥ 4.3 | Low |
| ≥ 3.3 | Moderate |
| ≥ 2.5 | High |
| < 2.5 | Speculative |

## Quick Start

1. **View the tracker**: Open `index.html` in a browser (or use a local server)
2. **Run automation**: `cd automation && python main.py`

## Adding YouTube Channels

Edit `automation/config/channels.json` to add or enable channels:

```json
{
  "id": "channel-id",
  "name": "Channel Name",
  "handle": "@ChannelHandle",
  "url": "https://www.youtube.com/@ChannelHandle/videos",
  "enabled": true,
  "description": "Channel description"
}
```

## Data Prompt (Manual)

Use this prompt in ChatGPT to generate structured stock data:

```text
I’m building a stock “undervaluation radar” table.  
For the following tickers:  
`DUOL ,CMG, ADBE, MELI, CRWV, CRM, SPGI, EFX, NFLX, ASML, MA`  
  
Use your latest available financial data + reasonable estimates and return **only** a JSON array (no commentary) in this exact shape, one object per ticker:
```json
[
  {
    "ticker": "ADBE",
    "name": "Adobe Inc.",
    "price": 0,
    "dcf": {
      "conservative": "0-0",
      "base": "0-0",
      "aggressive": "0-0"
    },
    "fcfQuality": 0,
    "roicStrength": 0,
    "revenueDurability": 0,
    "balanceSheetStrength": 0,
    "insiderActivity": 0,
    "valueRank": 0,
    "expectedReturn": 0,
    "lastUpdated": "YYYY-MM-DD"
  }
]
```

Rules:
- `price` = latest stock price in USD (number, not string).  Fetch the latest financial data for all the tickers.
- `dcf.conservative`, `dcf.base`, `dcf.aggressive` = intrinsic value ranges as strings `"low-high"` in USD, based on conservative/base/aggressive DCF-style assumptions.  
- All factor fields (`fcfQuality`, `roicStrength`, `revenueDurability`, `balanceSheetStrength`, `insiderActivity`, `valueRank`, `expectedReturn`) are **integers 1–5**, using these meanings:
  - 1 = very poor / very expensive / very low expected return  
  - 3 = average / fairly valued / normal expected return  
  - 5 = excellent / very cheap / very high expected return  
- `lastUpdated` = today’s date in ISO format, e.g. `"2025-03-01"`.  
- If you’re unsure of an exact number, use your best reasonable estimate but still provide a concrete value.  
- Do **not** include `undervaluationScore` or `riskLevel` in the JSON; I will compute those separately.  
- Output **only valid JSON** (no comments, no trailing commas, no extra text).
```

