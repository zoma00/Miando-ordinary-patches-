```md
![Python 3](https://img.shields.io/badge/Python_3-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![MetaTrader 5](https://img.shields.io/badge/MetaTrader_5-0055A4)
![MQL5](https://img.shields.io/badge/MQL5-0055A4)
![SSL/TLS](https://img.shields.io/badge/SSL/TLS-009639?logo=letsencrypt&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white)
```


# Miando — MT5 Forex Data Integration & Analytics

Miando ingests live Forex market data from a **Windows MetaTrader 5 (MT5) server** into a
**Dockerized Python + PostgreSQL pipeline on Linux**, then computes technical indicators and
structured "Pattern JSON" analytics for trading analysis and short-term prediction.

The heart of the project is **cross-platform integration**: MetaTrader 5 and its MQL5 scripting
language run **only on Windows**, while the analytics and storage stack runs in **Docker on
Linux**. Miando bridges the two.

## The integration challenge

MT5/MQL5 is Windows-only; the processing stack is Linux + Docker. Miando connects them through a
shared, SSL-secured database rather than a brittle custom API:

```
┌──────────────────────────────┐
│  Windows MT5 Server           │  MQL5 script collects live OHLC bars for
│  (MetaTrader 5 / MQL5)        │  XAUUSD, EURUSD, GBPUSD, USDJPY, USDCHF
└───────────────┬──────────────┘
                │  direct SSL PostgreSQL connection (Windows → Linux)
                ▼
┌──────────────────────────────┐
│  Linux · Docker               │  ohlc_data table enriched with
│  PostgreSQL (SSL/TLS)         │  mt5_collection_time, data_source,
│                               │  spread, trading_session
└───────────────┬──────────────┘
                │  Python data bridge — reads new rows, enriches them
                ▼
┌──────────────────────────────┐
│  Analytics & Pattern JSON      │  technical indicators, real-time spread,
│  (Python services)            │  session detection, 152-candle pattern
│                               │  vectors, 1-hour gain/loss prediction
└──────────────────────────────┘
```

**How the data crosses platforms:** the Windows MT5 server writes OHLC bars **directly into the
Linux PostgreSQL database over an SSL connection**. On the Linux side, `amir_data_bridge.py`
continuously reads new rows, enriches them (real-time spread from the latest M1 candle, trading
session detection), and feeds the Pattern JSON analytics. `amir_monitor.py` tracks data freshness
(time since the last MT5 collection) so stale data never drives analysis.

## Tech stack

| Layer | Technology |
|---|---|
| Market data source | MetaTrader 5 / MQL5 (Windows) |
| Cross-platform ingestion | Direct SSL PostgreSQL writes + Python data bridge |
| Storage | PostgreSQL with SSL/TLS, containerized |
| Processing | Python (`psycopg2`), technical-indicator engine |
| Orchestration | Docker Compose (multi-service) |
| Historical backfill | Dukascopy fetcher (`duka/`) |
| Testing | pytest suite |

## Services

Orchestrated via `docker-compose.yml`:

- **`miando-db`** — PostgreSQL with SSL; holds the trading schema and market data
- **`indikator-bot`** — Python bot that computes technical indicators (updates every 30s)
- **`patterns`** — Pattern JSON analytics: spread, session mapping, and prediction
- **`pgadmin`** — optional database admin UI

## Data pipeline

1. **Collect** — MT5 on Windows records live OHLC bars per symbol.
2. **Cross platforms** — the Windows server writes directly to the Linux PostgreSQL DB over SSL.
3. **Bridge** — `amir_data_bridge.py` reads new rows and adds spread + session data.
4. **Analyze** — the indicator bot computes ADX, ATR, RSI, MACD, Bollinger Bands, and more.
5. **Pattern JSON** — a 152-candle structure is built for vector matching and 1-hour max
   gain/loss prediction.
6. **Monitor** — `amir_monitor.py` reports how fresh the MT5 data is.

## Technical indicators

ADX · ATR · Bollinger Bands · CCI · EMA · MACD · OBV · RSI · SMA · Stochastic Oscillator · Williams %R

## Quick start

```bash
# 1. Configure environment (never commit real secrets)
cp .env.example .env            # set POSTGRES_PASSWORD, DB_PASSWORD, etc.

# 2. Generate SSL certificates (if not already present)
./generate_ssl.sh

# 3. Build and run the stack
docker-compose up --build
```

Endpoints:
- PostgreSQL: `localhost:5434` (SSL)
- Indicator bot: connects automatically
- pgAdmin: `localhost:8080`

Generate guaranteed-fresh pattern data:

```bash
cd patterns/json_split/
python3 pattern_json_live.py --force-fresh   # bypasses caching for current-day data
```

Run the tests:

```bash
pytest
```

## Database schema (highlights)

- **Trading:** `accounts`, `account_state`, `open_trades`, `closed_trades`, `planned_trades`
- **Market data:** `ohlc_data` (with `mt5_collection_time`, `data_source`, `spread`,
  `trading_session`) and `trading_snapshots` (Pattern JSON storage)

## Security

- **SSL/TLS on every PostgreSQL connection** — both Windows → Linux ingestion and service → DB.
- Certificates are generated by `generate_ssl.sh`; **keys are gitignored and never committed**.
- Secrets live in a gitignored `.env`; `.env.example` documents the required variables.
- Services run in isolated Docker containers.

## Project structure

```
miando-mt5-forex-integration/
├── docker-compose.yml         Multi-service orchestration
├── Dockerfile                 PostgreSQL with SSL
├── schema.sql                 Database schema
├── generate_ssl.sh            SSL certificate generation
├── amir_data_bridge.py        Windows MT5 → Linux data bridge (core integration)
├── amir_monitor.py            MT5 data-freshness monitoring
├── amir_dashboard.py          Integration status dashboard
├── indikator_bot/             Technical-indicator engine
├── patterns/json_split/       Pattern JSON analytics & prediction
├── duka/                      Dukascopy historical-data fetcher
├── tests/                     pytest test suite
└── docs/                      Design and methodology notes
```

## License

Proprietary — Miando trading platform.
