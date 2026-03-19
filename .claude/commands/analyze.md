# Analyze Stock

Run a full analysis pipeline for a stock ticker using the multi-agent MCP system.

## Usage
```
/analyze AAPL
```

## What it does
1. POSTs to `/api/analyze/{ticker}` — triggers all 9 agents
2. Reads the SSE stream at `/api/stream/{ticker}` for live events
3. Returns the full `AnalysisResult` with recommendation, debate, technicals, and news sentiment

## Useful for
- Testing the pipeline end-to-end
- Verifying agents complete without errors
- Checking recommendation quality

## Quick test via curl
```bash
curl -X POST http://localhost:8000/api/analyze/$ARGUMENTS
```

## View live agent activity
```bash
curl -N http://localhost:8000/api/stream/$ARGUMENTS
```
