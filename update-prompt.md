# The Joseph Carlson Show – Stock Data Update Prompt

Use this prompt to generate updated stock data for The Joseph Carlson Show stock tracker.

## Prompt

I'm building a stock tracker for The Joseph Carlson Show.
For the following tickers (categorize as Dividend or Growth):
`DUOL, CMG, ADBE, MELI, CRWV, CRM, SPGI, EFX, NFLX, ASML, MA`

Use your latest available financial data + reasonable estimates and return **only** a JSON array (no commentary) in this exact shape, one object per ticker:

```json
[
  {
    "category": "Growth",
    "ticker": "ADBE",
    "name": "Adobe Inc.",
    "price": 0,
    "initialPrice": 0,
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

## Rules

- `category` = either "Dividend" or "Growth" based on the stock's profile (dividend-paying mature companies vs. growth-focused companies).
- `price` = latest stock price in USD (number, not string). Fetch the latest financial data for all the tickers.
- `initialPrice` = the very first automation price for that ticker. If the ticker already exists in `data/stocks.json`, keep its previous `initialPrice`. Only populate `initialPrice` the first time a ticker is added (usually set equal to the fetched `price`).
- `dcf.conservative`, `dcf.base`, `dcf.aggressive` = intrinsic value ranges as strings `"low-high"` in USD, based on conservative/base/aggressive DCF-style assumptions.
- All factor fields (`fcfQuality`, `roicStrength`, `revenueDurability`, `balanceSheetStrength`, `insiderActivity`, `valueRank`, `expectedReturn`) are **integers 1–5**, using these meanings:
  - 1 = very poor / very expensive / very low expected return
  - 3 = average / fairly valued / normal expected return
  - 5 = excellent / very cheap / very high expected return
- `lastUpdated` = today's date in ISO format, e.g. `"2025-03-01"`.
- If you're unsure of an exact number, use your best reasonable estimate but still provide a concrete value.
- Do **not** include `undervaluationScore` or `riskLevel` in the JSON; I will compute those separately.
- Output **only valid JSON** (no comments, no trailing commas, no extra text).

## How to Apply to Existing Table

1. Run this prompt in ChatGPT or Claude Code
2. Get the JSON response with updated stock data
3. Update `data/stocks.json` with the new array (preserving any existing `initialPrice` values)
4. Verify each stock has a `category` field set to either "Dividend" or "Growth"
5. Test the table in the browser to verify all data displays correctly

## Column Determination Reference

**Input Data (from prompt):**
- Category (Dividend or Growth)
- Ticker, Name, Price, DCF ranges
- All factor scores (1-5 scale)

**Computed Columns (automatic in app.js):**
- Quality Summary = (fcfQuality + roicStrength) / 2
- Undervaluation Score = Weighted composite of all factors
- Risk Level = Based on average quality metrics
