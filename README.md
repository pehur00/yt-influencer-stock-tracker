# The Joseph Carlson Show – Stock Tracker

A comprehensive stock tracker for dividend and growth stocks featured on The Joseph Carlson Show.

**🔴 Live Site:** Deploy to GitHub Pages with automated weekly updates!

## Features

✨ **Automated Weekly Updates** - Crew.ai agents update stock data every Sunday
📊 **DCF Valuation Analysis** - Conservative, base, and aggressive scenarios
🎯 **Quality Scoring** - 7 factor scores (1-5 scale) for each stock
🏷️ **Category Classification** - Dividend vs. Growth stock categorization
🌐 **Free Hosting** - GitHub Pages with global CDN
🤖 **AI-Powered** - Multiple AI models via OpenRouter (Gemini, GPT-4, Claude, Llama)
💰 **$0 Cost** - Use free Gemini 2.0 Flash model (or choose paid models)

## Quick Start

### Deploy to GitHub Pages (Recommended)

**Quick Deploy (4 commands):**

```bash
gh repo create joseph-carlson-stock-tracker --public --source=. --push
gh secret set OPENROUTER_API_KEY  # Paste your free key from https://openrouter.ai/keys
# Enable Pages: Settings → Pages → Source: GitHub Actions
# Done! Live in ~2 min at https://[username].github.io/joseph-carlson-stock-tracker
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full guide and options.

### Local Development

```bash
python -m http.server 8000
# Open http://localhost:8000
```

## Manual Data Update Prompt

For manual updates or testing, use this prompt to generate structured stock data:

```text
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
- `category` = either "Dividend" or "Growth" based on the stock's profile (dividend-paying mature companies vs. growth-focused companies).
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

## Automation

This project includes a Crew.ai automation system that updates stock data weekly.

### Architecture

```
GitHub Actions (Weekly)
    ↓
Crew.ai Agents:
  1. Data Fetcher → Fetches latest prices
  2. Analyst → Calculates DCF & scores
  3. Formatter → Generates JSON
    ↓
data/stocks.json (Updated)
    ↓
GitHub Pages (Auto-deploys)
```

### Running Automation Locally

```bash
cd automation

# Set up environment
cp .env.example .env
# Add OPENROUTER_API_KEY to .env (get free key at https://openrouter.ai/keys)
# Optionally set CREW_MODEL (or OPENROUTER_MODEL) to pick which model to run
# Set CREW_TICKERS if you want to customize the tracked symbols (comma-separated)

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

See [automation/README.md](automation/README.md) for details.

## Project Structure

```
stocktable/
├── index.html              # Main HTML
├── styles.css             # Styling
├── app.js                 # Frontend logic
├── data/
│   └── stocks.json        # Stock data (auto-updated)
├── automation/            # Crew.ai automation
│   ├── agents/           # AI agents
│   ├── tools/            # Market data tools
│   ├── crew_config.py    # Crew orchestration
│   └── main.py           # Entry point
├── .github/
│   └── workflows/
│       ├── update-stocks.yml  # Weekly update
│       └── deploy-pages.yml   # GitHub Pages deploy
├── DEPLOYMENT.md         # Deployment guide
└── README.md            # This file
```

## Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Full deployment guide
- **[automation/README.md](automation/README.md)** - Automation details
- **[AGENTS.md](AGENTS.md)** - Technical overview
- **[update-prompt.md](update-prompt.md)** - Manual update guide

## Contributing

Tracked stocks are from The Joseph Carlson Show. To add/remove:

1. Edit `automation/crew_config.py` → `TICKERS` list
2. Commit and push
3. Next weekly run includes changes

## License

MIT

## Credits

Built for [The Joseph Carlson Show](https://www.youtube.com/@TheJosephCarlsonShow) community.

Powered by:
- [Crew.ai](https://www.crewai.com/) - AI agent orchestration
- [OpenRouter](https://openrouter.ai/) - Multi-model AI API (Gemini, GPT-4, Claude, Llama)
- [GitHub Pages](https://pages.github.com/) - Free hosting & CDN
