# Testing Guide

This guide helps you test the stock tracker locally before deploying.

## Testing the Website Locally

### 1. Test with Static Server

```bash
# Option 1: Python
python -m http.server 8000

# Option 2: Node.js
npx serve .

# Option 3: PHP
php -S localhost:8000
```

Open browser to `http://localhost:8000`

### 2. Verify Data Loading

**Expected behavior:**
1. Page loads with "Loading stock data..." message
2. Data loads from `data/stocks.json`
3. Table populates with 11 stocks
4. Stocks show category badges (Dividend/Growth)
5. Click any row to see details

**Troubleshooting:**
- **Blank table**: Check browser console for errors
- **CORS error**: Use a local server (not file://)
- **No data**: Verify `data/stocks.json` exists and is valid JSON

### 3. Validate JSON Data

```bash
# Check JSON syntax
python -m json.tool data/stocks.json > /dev/null && echo "✓ Valid JSON"

# Or using jq
jq empty data/stocks.json && echo "✓ Valid JSON"
```

**Required fields per stock:**
- category (string: "Dividend" or "Growth")
- ticker (string)
- name (string)
- price (number)
- dcf (object with conservative, base, aggressive)
- fcfQuality (1-5)
- roicStrength (1-5)
- revenueDurability (1-5)
- balanceSheetStrength (1-5)
- insiderActivity (1-5)
- valueRank (1-5)
- expectedReturn (1-5)
- lastUpdated (YYYY-MM-DD)

## Testing the Automation

### 1. Local Crew.ai Test

```bash
cd automation

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Add your OPENROUTER_API_KEY to .env"
    echo "Get free key at: https://openrouter.ai/keys"
    exit 1
fi

# Install dependencies
pip install -r requirements.txt

# Run automation
python main.py
```

**Expected output:**
```
======================================================================
  YouTube Influencer Stock Tracker - Automated Update
======================================================================

Starting YouTube Influencer Stock Tracker Crew...
Analyzing tickers: DUOL, CMG, ADBE, MELI, CRWV, CRM, SPGI, EFX, NFLX, ASML, MA
------------------------------------------------------------

[Agent outputs...]

------------------------------------------------------------
Crew execution completed!
✓ Copied stocks.json to ../data/stocks.json

The website will now display the updated data.
```

### 2. Verify Generated JSON

```bash
# Check that file was created
ls -lh automation/output/stocks.json
ls -lh data/stocks.json

# Validate JSON
python -m json.tool data/stocks.json | head -30

# Count stocks
cat data/stocks.json | jq length
# Should output: 11
```

### 3. Test Individual Agents

```python
# Test data fetcher
cd automation
python -c "
from agents.data_fetcher_agent import create_data_fetcher_agent
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-4o-mini')
agent = create_data_fetcher_agent(llm)
print('✓ Data fetcher agent created')
"

# Test analyst
python -c "
from agents.analyst_agent import create_analyst_agent
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-4o-mini')
agent = create_analyst_agent(llm)
print('✓ Analyst agent created')
"

# Test formatter
python -c "
from agents.formatter_agent import create_formatter_agent
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-4o-mini')
agent = create_formatter_agent(llm)
print('✓ Formatter agent created')
"
```

## Testing GitHub Actions Locally

Use [act](https://github.com/nektos/act) to test workflows locally:

```bash
# Install act
brew install act  # macOS
# or download from https://github.com/nektos/act

# Test update workflow
act workflow_dispatch \
    -j update-stock-data \
    -s OPENAI_API_KEY="your-key-here"

# Test deploy workflow
act push -j deploy
```

## Integration Tests

### 1. Full End-to-End Test

```bash
#!/bin/bash
set -e

echo "🧪 Running full integration test..."

# 1. Run automation
cd automation
python main.py
cd ..

# 2. Validate JSON
python -m json.tool data/stocks.json > /dev/null
echo "✓ JSON is valid"

# 3. Check stock count
count=$(cat data/stocks.json | jq length)
if [ "$count" -eq 11 ]; then
    echo "✓ All 11 stocks present"
else
    echo "✗ Expected 11 stocks, found $count"
    exit 1
fi

# 4. Start local server
python -m http.server 8000 &
SERVER_PID=$!
sleep 2

# 5. Test website loads
curl -s http://localhost:8000 | grep "Influencer Stock Tracker" > /dev/null
echo "✓ Website loads"

# 6. Test data endpoint
curl -s http://localhost:8000/data/stocks.json | jq empty
echo "✓ Data endpoint works"

# Cleanup
kill $SERVER_PID

echo "✅ All tests passed!"
```

Save as `test.sh`, make executable (`chmod +x test.sh`), and run.

### 2. Manual Smoke Tests

**Checklist before deploying:**

- [ ] Website loads locally without errors
- [ ] All 11 stocks display in table
- [ ] Category badges show correctly (blue/purple)
- [ ] Sorting works (dropdown changes order)
- [ ] Row expansion shows details
- [ ] DCF ranges display properly
- [ ] Factor scores are 1-5
- [ ] Last updated date is correct
- [ ] No console errors in browser
- [ ] JSON file is valid
- [ ] Automation runs without errors

## Performance Testing

### Load Time

```bash
# Measure page load time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000

# Create curl-format.txt:
echo "
    time_namelookup:  %{time_namelookup}s
       time_connect:  %{time_connect}s
    time_appconnect:  %{time_appconnect}s
   time_pretransfer:  %{time_pretransfer}s
      time_redirect:  %{time_redirect}s
 time_starttransfer:  %{time_starttransfer}s
                    ----------
         time_total:  %{time_total}s
" > curl-format.txt
```

### JSON Size

```bash
# Check data/stocks.json size
ls -lh data/stocks.json

# Should be < 10KB
# Typical: ~5-7KB
```

## Continuous Testing

### Pre-commit Checks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running pre-commit checks..."

# Validate JSON
if [ -f data/stocks.json ]; then
    python -m json.tool data/stocks.json > /dev/null || {
        echo "✗ Invalid JSON in data/stocks.json"
        exit 1
    }
    echo "✓ JSON is valid"
fi

# Check for console.log in JS
if grep -r "console\.log" *.js 2>/dev/null; then
    echo "⚠️  console.log found in JS files"
fi

echo "✓ Pre-commit checks passed"
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### Common Issues

**1. Automation fails with "OPENROUTER_API_KEY not found"**
```bash
# Check .env file
cat automation/.env | grep OPENROUTER_API_KEY

# Or export temporarily
export OPENROUTER_API_KEY=your-key-here
cd automation && python main.py

# Get free API key at: https://openrouter.ai/keys
```

**2. CORS errors in browser**
```
Use a local server, not file://
```

**3. Blank table on website**
```bash
# Check browser console
# Verify data/stocks.json exists
ls -l data/stocks.json

# Test JSON directly
curl http://localhost:8000/data/stocks.json
```

**4. GitHub Actions workflow fails**
```
1. Check Actions tab for logs
2. Verify OPENROUTER_API_KEY secret is set
3. Check for API rate limits (unlikely with free tier)
4. Try manual trigger to test
```

## Next Steps

Once all tests pass:
1. Commit changes
2. Push to GitHub
3. Enable GitHub Pages
4. Add OPENAI_API_KEY secret
5. Monitor first workflow run

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment steps.
