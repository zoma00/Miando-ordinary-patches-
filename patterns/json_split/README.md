# Miando JSON Split - Live Exporters

This package splits the monolithic `json_exporter.py` into 5 separate components that export different types of data to individual JSONB columns in the `trading_snapshots` table.

## 📁 **Project Structure**

```
patterns/json_split/
├── update_schema.sql         # 🗄️ Database schema updates
├── common.py                 # 🔧 Shared database utilities
├── main_live.py             # 🎮 Main coordinator script
├── main_history.py          # 📚 Historical backfill coordinator
├── ohlc_all_live.py         # 📊 OHLC data + indicators (live)
├── ohlc_all_history.py      # 📊 OHLC data + indicators (historical)
├── account_state_live.py    # 💰 Account balance/equity (live)
├── account_state_history.py # 💰 Account balance/equity (historical)
├── open_trades_live.py      # 📈 Open/pending trades (live)
├── open_trades_history.py   # 📈 Open/pending trades (historical)
├── closed_trades_live.py    # 📉 Recently closed trades (live)
├── closed_trades_history.py # 📉 Recently closed trades (historical)
├── market_state_live.py     # 🌍 Market volatility/session (live)
├── market_state_history.py  # 🌍 Market volatility/session (historical)
├── max_gain_loss_calc.py    # 🔍 Max gain/loss calculator (Feature 7)
└── README.md                # 📚 This file
```

## 🚀 **Quick Start**

### 1. **Database Setup**

First, apply the database schema updates:

```bash
# Connect to your PostgreSQL database and run:
psql -h miando-db -U miando -d miando -f update_schema.sql
```

### 2. **Test Database Connection**

```bash
cd /home/hazem/Miando/patterns/json_split
python main_live.py --test-db
```

### 3. **Run Single Export (Testing)**

```bash
# Run all exporters once
python main_live.py

# Run specific exporter
python ohlc_all_live.py
python account_state_live.py
```

### 4. **Run Continuous Export (Production)**

```bash
# Run every minute (default)
python main_live.py --continuous

# Run every 30 seconds
python main_live.py --continuous --interval 30
```

## 🔄 **Historical Data Backfill**

### 1. **Complete Historical Backfill**

```bash
# Backfill all data types for all historical snapshots
python main_history.py

# Backfill last week only
python main_history.py --last-week

# Backfill specific date range
python main_history.py --start-date 2024-01-01 --end-date 2024-12-31
```

### 2. **Selective Historical Backfill**

```bash
# Backfill only OHLC and account data
python main_history.py --data-types ohlc account

# Backfill only max gain/loss calculations
python main_history.py --data-types max_gain_loss

# Available data types:
# - ohlc: OHLC data + indicators
# - account: Account state data
# - open_trades: Open trades data
# - closed_trades: Closed trades data  
# - market: Market state data
# - max_gain_loss: Max gain/loss calculations (Feature 7)
```

### 3. **Individual Historical Scripts**

```bash
# Run individual historical exporters
python ohlc_all_history.py --last-month
python account_state_history.py --batch-size 500
python max_gain_loss_calc.py --mode historical
```

## 🔍 **Max Gain/Loss Calculator (Feature 7)**

The max gain/loss calculator analyzes OHLC snapshots to determine maximum potential gain and loss percentages over the next 60 minutes:

### **Live Mode:**
```bash
# Run continuous live calculations (calculates for snapshots exactly 60 minutes old)
python max_gain_loss_calc.py --mode live
```

### **Historical Mode:**
```bash
# Backfill historical calculations
python max_gain_loss_calc.py --mode historical --batch-size 100
```

### **Database Columns:**
- `max_gain_pct_1h`: Maximum gain percentage in next hour
- `max_loss_pct_1h`: Maximum loss percentage in next hour  
- `calculation_range_minutes`: Actual minutes of data used (60 = complete, <60 = partial)
- `prediction_mode`: TRUE if calculated with incomplete data (live mode)

## 📊 **Output Data Structure**

### **trading_snapshots Table Columns:**

| Column | Type | Description |
|--------|------|-------------|
| `ohlc_all_json` | JSONB | OHLC data + indicators for all timeframes |
| `account_state_json` | JSONB | Account balance, equity, margin data |
| `open_trades_json` | JSONB | Currently open/pending trades |
| `closed_trades_json` | JSONB | Recently closed trades |
| `market_state_json` | JSONB | Market volatility, spread, session |
| `max_gain_pct_1h` | DECIMAL(10,4) | Max gain % in next 60 minutes |
| `max_loss_pct_1h` | DECIMAL(10,4) | Max loss % in next 60 minutes |
| `calculation_range_minutes` | INTEGER | Minutes of data used for calculation |
| `prediction_mode` | BOOLEAN | TRUE if calculated with incomplete data |

### **JSON Structure Examples:**

#### **ohlc_all_json:**
```json
{
  "symbol": "XAUUSD",
  "timestamp": "2025-08-06T10:15:00Z",
  "ohlc": {
    "M1": [{"open_time": "...", "open": 2350.5, "high": 2351.0, "rsi": 45.2, ...}],
    "M5": [...],
    "H1": [...]
  },
  "ohlc_last_time": {"M1": "2025-08-06T10:15:00Z", "M5": "..."},
  "last_update": "2025-08-06T10:15:00Z"
}
```

#### **account_state_json:**
```json
{
  "timestamp": "2025-08-06T10:15:00Z",
  "balance": 1000.0,
  "equity": 995.0,
  "margin": 50.0,
  "free_margin": 945.0,
  "leverage": 500,
  "profit": -5.0,
  "currency": "USD"
}
```

#### **open_trades_json:**
```json
[
  {
    "symbol": "XAUUSD",
    "magic": 123456,
    "order_type": "buy",
    "lot_size": 0.10,
    "open_price": 2350.50,
    "sl": 2340.00,
    "tp": 2365.00,
    "open_time": "2025-08-06T10:15:00Z",
    "status": "open",
    "original_sl": 2340.00,
    "original_tp": 2365.00
  }
]
```

## 🔧 **Configuration**

All configuration is done via environment variables (already set in your existing setup):

```bash
DB_HOST=miando-db
DB_NAME=miando
DB_USER=miando
DB_PASSWORD=changeme
SYMBOL=XAUUSD
```

## 📈 **Database Queries**

### **View Latest Data:**

```sql
-- Latest OHLC data
SELECT jsonb_pretty(ohlc_all_json) 
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;

-- Latest account state
SELECT jsonb_pretty(account_state_json) 
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;

-- Latest open trades
SELECT jsonb_pretty(open_trades_json) 
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;

-- Max gain/loss analysis
SELECT 
  snapshot_time,
  max_gain_pct_1h,
  max_loss_pct_1h,
  calculation_range_minutes,
  prediction_mode
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
AND max_gain_pct_1h IS NOT NULL
ORDER BY snapshot_time DESC LIMIT 10;
```

### **Check Data Completeness:**

```sql
-- Count records with each JSON type
SELECT 
  COUNT(*) as total_snapshots,
  COUNT(ohlc_all_json) as ohlc_count,
  COUNT(account_state_json) as account_count,
  COUNT(open_trades_json) as trades_count,
  COUNT(closed_trades_json) as closed_count,
  COUNT(market_state_json) as market_count
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
AND snapshot_time >= NOW() - INTERVAL '1 day';
```

## 🐳 **Docker Integration**

### **Update docker-compose.yml:**

Add the JSON split exporters to your existing patterns service:

```yaml
patterns:
  build:
    context: ./patterns
    dockerfile: Dockerfile
  container_name: patterns-container
  depends_on:
    - miando-db
  volumes:
    - ./patterns:/app
    - ./server.crt:/app/server.crt:ro
    - ./server.key:/app/server.key:ro
  environment:
    DB_HOST: miando-db
    DB_PORT: 5432
    DB_NAME: miando
    DB_USER: miando
    DB_PASSWORD: changeme
    SYMBOL: XAUUSD
  command: python json_split/main_live.py --continuous
```

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **Database Connection Failed:**
   ```bash
   # Check database is running
   docker-compose ps
   
   # Test connection
   python -c "from json_split.common import get_pg_conn; print('DB OK')"
   ```

2. **Missing JSON Columns:**
   ```bash
   # Apply schema updates
   psql -f update_schema.sql
   ```

3. **No Data Being Exported:**
   ```bash
   # Check if M1 data exists
   python -c "from json_split.common import get_latest_m1_time; print(get_latest_m1_time('XAUUSD'))"
   ```

### **Debug Mode:**

```bash
# Run with detailed logging
python main_live.py --test-db
python ohlc_all_live.py  # Test individual components
```

## 📋 **Next Steps**

1. ✅ **Database schema updated**
2. ✅ **Live exporters implemented**
3. 🔄 **Historical exporters** (ohlc_all_history.py, etc.)
4. 🔄 **Max gain/loss calculations** (max_gain_loss_calc.py)
5. 🔄 **Docker containerization**
6. 🔄 **Production testing**

## 🤝 **Integration with Existing System**

This package integrates seamlessly with your current microservices architecture:

- **Keeps existing `json_exporter.py`** (doesn't break current functionality)
- **Uses same database and SSL certificates**
- **Same environment variables and Docker setup**
- **Runs alongside existing services**

The new JSON columns can be used by your AI/GPT analysis while maintaining backward compatibility with existing code.
