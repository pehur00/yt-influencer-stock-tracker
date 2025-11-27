# Deployment Guide: YouTube Influencer Stock Tracker

This guide explains how to deploy the stock tracker to GitHub Pages with automated weekly updates.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                          │
│                                                             │
│  Weekly Update       Data Generation      Deploy           │
│  (Sundays 6AM)  →   (Crew.ai + GPT)  →   (GitHub Pages)   │
│                                                             │
│  - Fetch prices     - DCF analysis        - Auto deploy    │
│  - Calculate DCF    - Factor scores       - Global CDN     │
│  - Format JSON      - Commit changes      - Free hosting   │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Website Updates
                    Automatically
```

## Prerequisites

1. **GitHub Account** (free)
2. **OpenRouter API Key** (free tier available!)
   - Sign up at: https://openrouter.ai/
   - Get API key: https://openrouter.ai/keys
3. **Git installed** locally

## Quick Deploy with GitHub CLI

**Easiest method - 4 commands:**

```bash
# 1. Create repo and push
gh repo create joseph-carlson-stock-tracker --public --source=. --push

# 2. Add OpenRouter API key (get free key at https://openrouter.ai/keys)
gh secret set OPENROUTER_API_KEY

# 3. (Optional) Set custom model
gh secret set OPENROUTER_MODEL -b "anthropic/claude-3.5-sonnet"

# 4. Enable GitHub Pages via web UI (see below) or manually:
# Settings → Pages → Source: GitHub Actions
```

**Done! Your site will be live in ~2 minutes** 🚀

## Step-by-Step Deployment (Manual)

### 1. Create GitHub Repository

```bash
# Initialize git if not already done
git init

# Add all files
git add .
git commit -m "Initial commit: YouTube Influencer Stock Tracker"

# Create repo on GitHub and push
gh repo create youtube-stock-tracker --public --source=. --push
```

### 2. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under "Build and deployment":
   - Source: **GitHub Actions**
4. Save changes

### 3. Add OpenRouter API Secret

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `OPENROUTER_API_KEY`
4. Value: Your OpenRouter API key (from https://openrouter.ai/keys)
5. Click **Add secret**

**💡 Tip:** OpenRouter offers free models like Gemini 2.0 Flash, so you can run this at $0 cost!

### 4. Verify Workflows

1. Go to **Actions** tab
2. You should see two workflows:
   - ✅ **Deploy to GitHub Pages** (runs on push)
   - ✅ **Update Stock Data Weekly** (runs Sundays)

### 5. Test Manual Update

Trigger the stock update manually:

1. Go to **Actions** → **Update Stock Data Weekly**
2. Click **Run workflow** → **Run workflow**
3. Wait ~2-5 minutes for completion
4. Check that `data/stocks.json` was updated (new commit)

### 6. Access Your Site

Your site will be live at:
```
https://<your-username>.github.io/joseph-carlson-stock-tracker/
```

Or if you set a custom domain:
```
https://your-domain.com
```

## Automatic Updates

### Weekly Schedule

- **When**: Every Sunday at 6:00 AM UTC
- **What happens**:
  1. Crew.ai agents fetch latest prices
  2. Calculate new DCF valuations and scores
  3. Update `data/stocks.json`
  4. Commit and push changes
  5. GitHub Pages auto-redeploys (2-3 min)
  6. Website shows fresh data

### Manual Trigger

Force an update anytime:
1. Actions → Update Stock Data Weekly
2. Run workflow → Run workflow

## Custom Domain (Optional)

### Add Custom Domain

1. Buy a domain (Namecheap, Google Domains, etc.)
2. In GitHub: Settings → Pages → Custom domain
3. Enter your domain (e.g., `stocks.josephcarlson.com`)
4. Configure DNS records at your registrar:

```
Type    Name    Value
CNAME   www     <your-username>.github.io
A       @       185.199.108.153
A       @       185.199.109.153
A       @       185.199.110.153
A       @       185.199.111.153
```

5. Wait for DNS propagation (5-30 min)
6. Enable HTTPS in GitHub Pages settings

## Costs

| Service | Cost |
|---------|------|
| GitHub Pages | **$0** (100GB bandwidth/month) |
| GitHub Actions | **$0** (2,000 free minutes/month) |
| OpenRouter API (Gemini 2.0 Flash - default) | **$0** (free tier) |
| Custom Domain | **$10-15/year** (optional) |
| **Total** | **$0/month** or **$10-15/year** (domain only) |

**💰 Optional Paid Models:**
- GPT-4o-mini: ~$1-1.50/month
- Claude 3.5 Sonnet: ~$2-3/month
- Llama 3.3 70B: ~$0.50-1/month

Change model in `.env`: `OPENROUTER_MODEL=anthropic/claude-3.5-sonnet`

## Updating Tracked Stocks

To add/remove stocks from the tracker:

1. Edit `automation/crew_config.py`
2. Modify the `TICKERS` list:
   ```python
   TICKERS = [
       "DUOL", "CMG", "ADBE",  # Add/remove tickers here
   ]
   ```
3. Commit and push changes
4. Next weekly run will include the new stocks

## Monitoring

### Check Workflow Status

- **Actions tab**: See all workflow runs
- **Email notifications**: GitHub sends emails on failures
- **Commit history**: Each update creates a commit

### Debugging Failed Runs

1. Go to Actions → Failed workflow
2. Click the failed job
3. Expand steps to see logs
4. Common issues:
   - Missing OPENAI_API_KEY secret
   - API rate limits
   - Invalid JSON output (rare)

## Rollback

If bad data gets committed:

```bash
# Find the last good commit
git log --oneline data/stocks.json

# Revert to that commit
git revert <commit-hash>
git push
```

## Alternative Deployment Options

### Vercel (Alternative to GitHub Pages)

Faster builds, better performance:

1. Import repo at [vercel.com](https://vercel.com)
2. Deploy as static site
3. Add OPENAI_API_KEY to Vercel environment variables
4. Same GitHub Actions workflow works

### Netlify (Alternative)

Similar to Vercel:

1. Import repo at [netlify.com](https://netlify.com)
2. Build command: (none, it's static)
3. Publish directory: `/`
4. Add OPENAI_API_KEY to environment variables

## Advanced: Local Development

Run the site locally:

```bash
# Simple HTTP server
python -m http.server 8000

# Or use npx
npx serve .

# Open browser
open http://localhost:8000
```

Test automation locally:

```bash
cd automation

# Create .env with OPENAI_API_KEY
cp .env.example .env
# Edit .env and add your key

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Support

- **GitHub Issues**: [Report bugs/issues](https://github.com/your-repo/issues)
- **Workflow Logs**: Check Actions tab for detailed logs
- **Crew.ai Docs**: [https://docs.crewai.com](https://docs.crewai.com)

## Useful GitHub CLI Commands

```bash
# View repository in browser
gh repo view --web

# Check workflow runs
gh run list
gh run watch  # Monitor latest run

# View secrets (names only, not values)
gh secret list

# Update a secret
gh secret set OPENROUTER_MODEL -b "openai/gpt-4o-mini"

# Manually trigger stock update
gh workflow run update-stocks.yml

# View Pages deployment
gh api repos/:owner/:repo/pages

# Clone on another machine
gh repo clone your-username/joseph-carlson-stock-tracker
```

## Next Steps

✅ Site is live and auto-updating weekly!

**Optional Enhancements:**
- [ ] Add real-time premium market data integration
- [ ] Implement caching to reduce API costs
- [ ] Add historical data tracking
- [ ] Create email/Discord notifications on updates
- [ ] Add mobile-responsive improvements
- [ ] Integrate with more YouTube finance channels
