# Stock Screener

Run the stock screener to find highest-potential picks from a ~50 stock universe.

## Usage
```
/screen
/screen 10
```

## What it does
Queries `/api/screen?top_n=N` which:
1. Fetches Finnhub quotes + metrics for all ~50 stocks in parallel
2. Scores each by: 40% momentum + 30% RSI oversold bias + 30% 52-week range upside
3. Returns top N picks with full scoring breakdown

## Quick test
```bash
curl "http://localhost:8000/api/screen?top_n=$ARGUMENTS" | python3 -m json.tool
```

## Response fields per pick
- `ticker` — symbol
- `price` — current price
- `change_pct` — daily % change
- `rsi_14` — RSI (oversold < 30, overbought > 70)
- `range_position_pct` — position in 52-week range (0% = at 52w low, 100% = at 52w high)
- `composite_score` — overall score (higher = more potential)
