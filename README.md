# QX-Core (Demo)

A full-stack platform for systematic trading research and monitoring: FastAPI
backend, Next.js/TypeScript dashboard, live WebSocket updates, async job queue,
a cost-aware backtester with a statistical validation battery, a market-data
pipeline, Prometheus/Grafana monitoring and Docker Compose deployment.

**This is a portfolio/demo version of a private project.** The real trading
strategies, their research and live market data are intentionally not included
here — this repo shows the surrounding engineering (API design, validation
methodology, data pipeline, observability, deployment), not proprietary trading
logic. The "strategy" wired up here is a plain EMA20/EMA50 crossover with an RSI
filter running on synthetically generated price data (seeded geometric Brownian
motion) — deliberately unremarkable. It has no edge, and the validation tools
below are expected to say so.

## Stack

- **Backend**: Python 3.12, FastAPI, Pydantic, pandas, NumPy, SciPy, CCXT,
  SQLite (optional migration to PostgreSQL), optional Redis, prometheus-client.
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS,
  [lightweight-charts](https://github.com/tradingview/lightweight-charts) for
  candlesticks and the equity curve.
- **Infra**: Docker Compose (multi-stage images, healthchecks, named volumes),
  Prometheus + Grafana, GitHub Actions CI.
- **Quality**: pytest (67 tests, ~92% coverage), ruff, mypy, pre-commit, TypeScript strict mode.

## Running it

```bash
docker compose up --build
```

- Dashboard: http://localhost:3010
- API: http://localhost:8010 (docs at `/docs`)

No API keys, no external services: the backend generates its synthetic dataset
in memory on startup, so it works completely offline.

```bash
# + Prometheus :9090 and Grafana :3001 (needs GRAFANA_ADMIN_PASSWORD)
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# + PostgreSQL with scheduled dumps, and Redis (needs POSTGRES_PASSWORD)
docker compose -f docker-compose.yml -f docker-compose.data.yml up -d
```

Without Docker:

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn main:app --reload
.venv/bin/pytest

# frontend (separate terminal)
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8010 npm run dev
```

## What is in it

### API (REST + WebSocket)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Aggregate status: API, database, Redis, kill switch and every engine heartbeat (`degraded` if one is stale or halted) |
| `GET /metrics` | Prometheus metrics |
| `GET /api/snapshot`, `/candles`, `/trades` | Current state of the demo engine |
| `POST /api/backtest/run`, `GET /api/backtest/run/{id}` | Async backtest job (start, then poll) |
| `POST /api/validation/run`, `GET /api/validation/run/{id}` | Async validation job (see below) |
| `GET /api/runs` | Persisted history of finished jobs |
| `GET/POST /api/halt`, `POST /api/resume` | Kill switch: pause or resume the engine |
| `POST /api/auth/login`, `/logout`, `GET /api/auth/verify` | Session-cookie login |
| `WS /api/ws` | Live snapshot push |

Access is open by default. Set `DASHBOARD_API_KEY` to require an `X-API-Key`
header (and `?api_key=` on the WebSocket), and/or the `DASHBOARD_ADMIN_*` variables
for a session login with a PBKDF2 password hash, an HMAC-signed HttpOnly cookie and a
login rate limit (see `.env.example`). The dashboard shows a sign-in form when login is on.

### Backtesting and validation (`backend/quant/`)

- **Cost model** (`costs.py`): exchange fee on every fill plus ATR-scaled
  slippage with a floor. Costs are always modelled.
- **No look-ahead**: a signal on bar `t` uses data up to `t-1`; fills happen at
  the open of `t`.
- **Metrics** (`metrics.py`): CAGR, volatility, Sharpe, Sortino, Calmar, max
  drawdown, VaR/CVaR, profit factor, win rate.
- **Walk-forward analysis** (`walkforward.py`): expanding windows, in-sample
  selection, out-of-sample scoring, embargo between train and test.
- **Deflated Sharpe ratio** (`statistics.py`): corrects the winner's Sharpe for
  the number of candidates tried.
- **Monte Carlo** (`monte_carlo.py`): bootstraps the trade list to size path
  risk (return and drawdown percentiles, probability of loss).
- The dashboard's **Validation** tab runs the whole battery over a small
  parameter grid.

### Market-data pipeline (`backend/marketdata/`)

```bash
python -m marketdata.cli fetch --symbol BTC/USDT --timeframe 1h --days 90
python -m marketdata.cli quality --symbol BTC/USDT --timeframe 1h
```

- Paginated OHLCV download through CCXT (public endpoints), dropping the bar
  still forming.
- SQLite store with upserts, plus a quality report (duplicates, missing bars,
  invalid OHLC, non-positive prices).
- `migrate_to_postgres.py` copies the store to PostgreSQL, refuses to overwrite
  without `--replace`, and verifies row counts after the copy
  (`--dry-run` to preview).

### Multi-worker mode (`backend/redis_store.py`)

With `REDIS_URL` set, job state lives in Redis and one elected worker publishes the
snapshot that every worker serves, so several API workers stay consistent. Without
Redis everything runs in process memory.

### Observability and operations (`backend/observability/`)

- Prometheus metrics: request count and latency per route, job counts and
  durations, engine equity, heartbeat age, connected WebSocket clients.
- File-based engine heartbeats, readable by the API and by a Docker
  `HEALTHCHECK` (`python -m observability.health <engine> --max-age 60`).
- Structured JSON logs with daily rotation (`QX_LOG_DIR`).
- File-based kill switch (`.HALT` sentinel): pauses the engine and marks `/health` as degraded.
- Rotating `pg_dump` backups of the optional PostgreSQL service (`infra/postgres/backup.sh`).
- Provisioned Grafana dashboard ("Algo Dashboard — Health").
- Telegram/Slack alerts when a background job fails (`alerts.py`).

## Project layout

```
backend/
  main.py             FastAPI entrypoint, middleware, /health
  routes.py           REST + WebSocket endpoints, async job pattern
  demo_engine.py      synthetic OHLCV generator + demo EMA-crossover backtest
  auth.py             API-key and session-cookie access control
  auth_session.py     password hashing, signed session tokens, login rate limit
  redis_store.py      optional shared job store and snapshot hub
  alerts.py           Telegram / Slack notifier
  quant/              costs, metrics, walk-forward, deflated Sharpe, Monte Carlo
  marketdata/         CCXT provider, SQLite store, quality checks, Postgres migration
  observability/      Prometheus metrics, heartbeats, kill switch, JSON logging
  tests/              pytest suite
frontend/
  src/app/            Next.js App Router page + layout
  src/components/     charts, KPIs, trades table, backtest and validation labs
  src/lib/api.ts      typed REST/WebSocket client
infra/monitoring/     Prometheus config and provisioned Grafana dashboard
infra/postgres/       scheduled pg_dump backup script
docker-compose.yml
.github/              CI (ruff, mypy, pytest, tsc, eslint, next build) and Dependabot
```

## What this demonstrates

- REST + WebSocket API design in FastAPI, with an async job queue for work too
  slow to run inline and persisted job history.
- A research workflow that tries to disprove a strategy: costs, no look-ahead,
  walk-forward, deflated Sharpe and Monte Carlo.
- A market-data pipeline with explicit quality checks and a verified database
  migration path.
- Production-minded operations: metrics, heartbeats, healthchecks, structured
  logs, alerting, a kill switch, backups and a provisioned dashboard.
- Access control with API keys and a hardened session login.
- A typed frontend data layer, containerized multi-service setup and CI.

## License

[MIT](./LICENSE)
