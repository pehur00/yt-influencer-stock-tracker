# AGENTS – YouTube Influencer Stock Tracker

This repo contains a small, static web app for tracking **dividend and growth stocks** featured by YouTube finance influencers via a scoring framework.

## Purpose

- Render a table of stocks recommended by YouTube finance channels with:
  - Category classification (Dividend vs. Growth)
  - DCF bands (conservative/base/aggressive)
  - 1–5 factor scores (FCF quality, ROIC, durability, balance sheet, insider activity, value rank, expected return)
  - Aggregated Undervaluation Score (0–100) and Risk Level.
  - Source attribution (which channel recommended the stock)
- Let the user quickly see which stocks look most attractive on a risk-adjusted basis.

## Current implementation

- `index.html` – YouTube Influencer Stock Tracker branded UI shell (hero, legend, table container).
- `styles.css` – Dark, neon-glass design system for the tracker.
- `app.js` – In-browser logic:
  - Hard-coded `stockData` array with category classification (Dividend/Growth).
  - Weighted Undervaluation Score computation.
  - Risk Level derivation from quality factors.
  - Sorting and row expansion for detailed factor/DCF breakdowns.
- `README.md` – Contains the prompt template for generating structured stock JSON.
- `update-prompt.md` – Contains the update prompt and instructions for applying new data to the table.
- `automation/` – CrewAI-powered automation for:
  - Fetching videos from multiple YouTube channels
  - Discovering new stock recommendations
  - Running financial analysis and DCF valuations
  - Multi-channel support with source attribution

## Conventions for changes

- Keep the app **static and framework-free** (plain HTML/CSS/JS) unless there is a strong reason to introduce a build system.
- When adding or changing the data model:
  - Prefer updating a single source (e.g. `stockData` in `app.js` or a future `data/stocks.json`).
  - Keep field names consistent with the spec (e.g. `category`, `fcfQuality`, `roicStrength`, `valueRank`, `expectedReturn`).
  - Ensure all stocks have a `category` field set to either "Dividend" or "Growth".
- When adjusting scoring logic:
  - Follow the weighting and 1–5 mapping described in the spec.
  - If weights or rules change, document the rationale briefly in `README.md` or a future `docs/` note.

## Future direction

- Replace static `stockData` with data generated from:
  - An external fundamentals API (e.g. via MCP servers like Alpha Vantage), or
  - A spreadsheet/Sheets → JSON pipeline.
- Keep most computation (scores, DCF bands) in a reproducible script rather than hand-editing JSON.
- Support more YouTube channels via `automation/config/channels.json`

