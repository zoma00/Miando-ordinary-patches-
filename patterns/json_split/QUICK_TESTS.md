# Quick Test Commands - Pattern JSON Live System

## ⚠️ Execution Environment
**Tests should be run on the HOST SYSTEM** (not inside containers) for best results.

## Instant System Check
```bash
# SUPER FAST health check (≤5 seconds) (RUN ON HOST)
/home/hazem/Miando/patterns/json_split/run_super_fast_tests.sh

# FAST comprehensive test suite (≤10 seconds) (RUN ON HOST)
/home/hazem/Miando/patterns/json_split/run_fast_tests.sh

# Individual pattern generation test (RUN ON HOST)
cd /home/hazem/Miando/patterns/json_split && python3 pattern_json_live.py

# Alternative: Container execution (if needed)
docker exec -it patterns-container python3 /app/patterns/json_split/pattern_json_live.py
```

## Database Quick Checks

### Latest Pattern Status (FAST)
```bash
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    snapshot_time,
    pattern_json->'volatility' as volatility,
    pattern_json->'session' as session,
    jsonb_array_length(pattern_json->'context'->'D1') +
    jsonb_array_length(pattern_json->'context'->'H4') +
    jsonb_array_length(pattern_json->'context'->'H1') +
    jsonb_array_length(pattern_json->'context'->'M15') +
    jsonb_array_length(pattern_json->'context'->'M5') +
    jsonb_array_length(pattern_json->'context'->'M1') as total_candles,
    length(pattern_json::text) as json_size_bytes
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"
```

### Enhanced Volatility Check
```bash
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    pattern_json->'volatility' as classification,
    pattern_json->'volatility_metrics'->'price_range_1h' as range_1h,
    pattern_json->'volatility_metrics'->'price_range_4h' as range_4h,
    pattern_json->'indicators'->'atr'->'H1' as atr_h1,
    pattern_json->'indicators'->'atr'->'H4' as atr_h4
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"
```

### Pattern Structure Validation
```bash
docker exec -it miando-db psql -U miando -d miando -c "
SELECT jsonb_pretty(pattern_json) 
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"
```

## Performance Checks

### Execution Timing
```bash
# Time execution on HOST
time (cd /home/hazem/Miando/patterns/json_split && python3 pattern_json_live.py)

# Time execution in container (comparison)
time docker exec -it patterns-container python3 /app/patterns/json_split/pattern_json_live.py
```

### Storage Efficiency (FAST)
```bash
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    (SELECT COUNT(*) FROM trading_snapshots WHERE symbol = 'XAUUSD' LIMIT 1000) as sample_snapshots,
    pg_size_pretty(pg_total_relation_size('trading_snapshots')) as table_size,
    (SELECT length(pattern_json::text) FROM trading_snapshots 
     WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1) as latest_json_size_bytes
;"

# Quick record count (limited for speed)
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 'Records found: ' || COUNT(*) as status 
FROM (SELECT 1 FROM trading_snapshots WHERE symbol = 'XAUUSD' LIMIT 100) as sample;"
```

## Symbol Configuration Test

### Change Symbol (if needed)
```bash
# Edit common.py to change symbol
sed -i 's/SYMBOL = ".*"/SYMBOL = "XAUUSD"/' /home/hazem/Miando/patterns/json_split/common.py

# Verify symbol setting
grep "SYMBOL =" /home/hazem/Miando/patterns/json_split/common.py
```

### Verify OHLC Data Availability
```bash
docker exec -it miando-db psql -U miando -d miando -c "
SELECT timeframe, COUNT(*) as records, 
       MIN(open_time) as earliest, MAX(open_time) as latest
FROM ohlc_data 
WHERE symbol = 'XAUUSD' 
GROUP BY timeframe ORDER BY timeframe;"
```

## Error Diagnosis

### Check Recent Logs (if logging to file)
```bash
tail -50 /home/hazem/Miando/patterns/miando/logs/json_exporter.log
```

### Debug Database Connection
```bash
docker exec -it miando-db psql -U miando -d miando -c "SELECT NOW();"
```

### Check Docker Containers
```bash
docker ps | grep -E "(miando-db|patterns)"
```

## Volatility Analysis Deep Dive

### ATR Indicator Analysis
```bash
docker exec -it miando-db psql -U miando -d miando -c "
SELECT timeframe, atr, rsi, ema
FROM ohlc_data 
WHERE symbol = 'XAUUSD' 
AND atr IS NOT NULL
ORDER BY timeframe, open_time DESC 
LIMIT 20;"
```

### Price Movement Analysis
```bash
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    open_time,
    high_price - low_price as price_range,
    close_price,
    atr
FROM ohlc_data 
WHERE symbol = 'XAUUSD' AND timeframe = 'H1'
ORDER BY open_time DESC 
LIMIT 10;"
```

## Expected Results Reference

### Successful Pattern Generation
- **Total Candles**: 152 (D1:7, H4:5, H1:20, M15:30, M5:30, M1:60)
- **Volatility**: One of: high, medium, low, high_price, medium_price, low_price, no_data
- **Session**: Sydney, London, or New York
- **Execution Time**: < 5 seconds
- **Storage**: JSONB format in trading_snapshots table

### XAUUSD Volatility Thresholds
- **H1 ATR High**: > $15.0
- **H1 ATR Medium**: > $8.0  
- **H4 ATR High**: > $25.0
- **H4 ATR Medium**: > $12.0
- **4H Price Range High**: > $20.0
- **1H Price Range High**: > $8.0

### Database Schema Check
```bash
docker exec -it miando-db psql -U miando -d miando -c "
\d trading_snapshots
\d ohlc_data"
```

---
**Quick Reference**: Run `/home/hazem/Miando/patterns/json_split/run_tests.sh` for comprehensive automated testing
