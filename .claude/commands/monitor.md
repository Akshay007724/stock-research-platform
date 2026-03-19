# Monitor Platform Health

Check live health of all API providers, Redis, and last pipeline run metrics.

## Usage
```
/monitor
```

## What it checks
- **Finnhub** — real-time quote latency
- **FMP** — fundamentals API latency
- **Stooq** — OHLCV CSV endpoint latency
- **Redis** — ping latency
- **Last pipeline** — total elapsed time, phase breakdown, API success rate

## Quick test
```bash
curl http://localhost:8000/api/monitor | python3 -m json.tool
```

## Response shape
```json
{
  "overall": "healthy | degraded",
  "providers": {
    "finnhub": { "status": "ok", "latency_ms": 123 },
    "fmp": { "status": "ok", "latency_ms": 95 },
    "stooq": { "status": "ok", "latency_ms": 210 }
  },
  "redis": { "status": "ok", "latency_ms": 1.2 },
  "last_pipeline": {
    "ticker": "AAPL",
    "total_elapsed_s": 8.4,
    "phase_times_s": {
      "phase1_historical_news": 2.1,
      "phase2_market": 0.9,
      "phase2b_debate": 4.2,
      "phase3_recommender": 1.1
    },
    "api_success_rate": 1.0
  }
}
```
