# Algo Trading Dashboard (Demo)

A full-stack dashboard for a systematic trading system: FastAPI backend,
Next.js/TypeScript frontend, Docker Compose deployment, live WebSocket
updates, and an async job queue for on-demand backtests.

**This is a portfolio/demo version of a private project.** The real trading
strategy, its research, and live market data are intentionally not included
here — this repo exists to show the surrounding engineering (API design,
frontend architecture, real-time updates, containerized deployment), not
proprietary trading logic. The "strategy" wired up here is a plain
EMA20/EMA50 crossover with an RSI filter running on synthetically generated
price data (seeded geometric Brownian motion) — deliberately unremarkable,
chosen only to give the UI something real to display end-to-end.

## Stack

- **Backend**: FastAPI, Pydantic, async job pattern for long-running
  backtests (`POST /api/backtest/run` → poll `GET /api/backtest/run/{id}`),
  WebSocket endpoint for live price/equity updates, optional API-key auth
  middleware.
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS,
  [lightweight-charts](https://github.com/tradingview/lightweight-charts)
  for candlestick/equity visualization, a small typed API client, a
  WebSocket hook for live state.
- **Infra**: Docker Compose (two services: `api`, `dashboard`), multi-stage
  Dockerfiles (Next.js standalone output for a minimal runtime image).

## Running it

```bash
docker compose up --build
```

- Dashboard: http://localhost:3010
- API: http://localhost:8010 (docs at `/docs`)

No API keys, no external services, no database — the backend generates its
synthetic dataset in memory on startup, so it works completely offline.

### Running without Docker

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload

# frontend (separate terminal)
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8010 npm run dev
```

## Project layout

```
backend/
  main.py          FastAPI app entrypoint, CORS, background task
  routes.py        REST + WebSocket endpoints
  demo_engine.py   synthetic OHLCV generator + demo EMA-crossover backtest
  models.py        Pydantic response models
  auth.py          optional API-key middleware
frontend/
  src/app/         Next.js App Router page + layout
  src/components/  chart, KPI, table, and backtest-lab UI components
  src/lib/api.ts   typed REST/WebSocket client
docker-compose.yml
```

## What this demonstrates

- REST + WebSocket API design in FastAPI, with an async job-queue pattern
  for operations too slow to run inline on the request.
- A typed frontend data layer talking to that API, with a live WebSocket
  subscription alongside a one-time initial fetch.
- Chart integration (candlesticks + equity curve) with a real charting
  library, not a toy canvas implementation.
- A containerized, multi-service local dev/deploy setup with multi-stage
  Docker builds.

## License

[MIT](./LICENSE)
