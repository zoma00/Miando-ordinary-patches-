# Pattern JSON Live System - Testing Guide

## Overview
This guide provides comprehensive testing procedures for the Pattern JSON Live system, which exports optimized OHLC data with enhanced volatility assessment for XAUUSD (Gold) trading analysis.

## System Architecture
- **Main Script**: `pattern_json_live.py` - Live pattern exporter with enhanced volatility assessment
- **Utilities**: `common.py` - Database utilities and helper functions
- **Database**: PostgreSQL with `trading_snapshots` and `ohlc_data` tables
- **Target Symbol**: XAUUSD (Gold)
- **Update Frequency**: Every minute

## Container vs Host Testing Options

### ✅ Recommended: Host Testing
**Why run tests on the host:**
- Direct file access to `/home/hazem/Miando/patterns/json_split/`
- Real production environment simulation
- Better debugging and log access
- Simpler dependency management
- No volume mounting complications

### 🔧 Alternative: Container Testing
**If you must test inside a container:**

```bash
# Option 1: Execute in existing patterns container
docker exec -it patterns-container python3 /app/patterns/json_split/pattern_json_live.py

# Option 2: Run automated test script in container
docker exec -it patterns-container /app/patterns/json_split/run_tests.sh

# Option 3: Create temporary test container
docker run --rm -it \
  --network miando-network \
  -v /home/hazem/Miando/patterns:/app/patterns \
  python:3.11 bash -c "
    cd /app/patterns/json_split && 
    apt update && apt install -y python3-psycopg2 && 
    python3 pattern_json_live.py"
```

**Container testing considerations:**
- Requires proper volume mounting (`-v /home/hazem/Miando/patterns:/app/patterns`)
- Network connectivity to database (`--network miando-network`)
- Dependencies must be installed in container
- File paths may differ (`/app/patterns/` vs `/home/hazem/Miando/patterns/`)

## Test Execution Environment

**⚠️ IMPORTANT: Tests should be run on the HOST SYSTEM (outside containers)**

The Pattern JSON Live system is designed to run on the host with Docker containers providing database services. Here's why:

### Host vs Container Testing:
- **✅ Run on Host**: Direct access to files, better debugging, real production environment
- **❌ Not in Container**: Limited file access, complex volume mounting, not representative of production

## Pre-Testing Setup

### 1. Environment Verification
```bash
# Verify Docker containers are running (run on HOST)
docker ps | grep -E "(miando-db|patterns)"

# Check database connectivity (from HOST to container)
docker exec -it miando-db psql -U miando -d miando -c "SELECT version();"

# Verify Python environment on HOST system
cd /home/hazem/Miando/patterns/json_split
python3 -c "import psycopg2, json; print('Dependencies OK')"

# Install required dependencies if missing
sudo apt update && sudo apt install -y python3-psycopg2
```

### 2. Database Schema Verification
```bash
# Check required tables exist
docker exec -it miando-db psql -U miando -d miando -c "
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('ohlc_data', 'trading_snapshots');"

# Verify OHLC data availability for XAUUSD
docker exec -it miando-db psql -U miando -d miando -c "
SELECT timeframe, COUNT(*) as records, 
       MIN(open_time) as earliest, MAX(open_time) as latest
FROM ohlc_data 
WHERE symbol = 'XAUUSD' 
GROUP BY timeframe ORDER BY timeframe;"
```

## Core Functionality Tests

### 1. Pattern JSON Generation Test
```bash
# Test main pattern JSON generation (RUN ON HOST)
cd /home/hazem/Miando/patterns/json_split
python3 pattern_json_live.py

# Expected output should show:
# - "Building pattern JSON for XAUUSD at [timestamp]"
# - "Fetched X pattern candles for [timeframe]" for each timeframe
# - "Built pattern JSON with 6 timeframes"
# - "Stored pattern JSON for XAUUSD"
# - "Pattern JSON export completed successfully"

# Alternative: If you must test inside container, use:
# docker exec -it patterns-container python3 /app/patterns/json_split/pattern_json_live.py
# (Note: This requires proper volume mounting and may have different behavior)
```

### 2. Database Storage Verification
```bash
# Quick check if pattern JSON was stored successfully (FAST)
docker exec -it miando-db psql -U miando -d miando -c "
SELECT symbol, snapshot_time, 
       pattern_json->'volatility' as volatility,
       jsonb_pretty(pattern_json->'volatility_metrics') as metrics
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"

# Optional: Count total records (slower for large datasets)
# docker exec -it miando-db psql -U miando -d miando -c "
# SELECT COUNT(*) as total_records FROM trading_snapshots WHERE symbol = 'XAUUSD';"
```

### 3. Timeframe Data Validation
```bash
# Verify all required timeframes are included
docker exec -it miando-db psql -U miando -d miando -c "
SELECT jsonb_object_keys(pattern_json->'context') as timeframes
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"

# Expected output: D1, H4, H1, M15, M5, M1
```

### 4. Candle Count Optimization Test
```bash
# Verify optimized candle counts per timeframe
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    jsonb_array_length(pattern_json->'context'->'D1') as D1_candles,
    jsonb_array_length(pattern_json->'context'->'H4') as H4_candles,
    jsonb_array_length(pattern_json->'context'->'H1') as H1_candles,
    jsonb_array_length(pattern_json->'context'->'M15') as M15_candles,
    jsonb_array_length(pattern_json->'context'->'M5') as M5_candles,
    jsonb_array_length(pattern_json->'context'->'M1') as M1_candles
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"

# Expected counts: D1:7, H4:5, H1:20, M15:30, M5:30, M1:60
```

## Enhanced Volatility Assessment Tests

### 1. ATR-Based Volatility Test
```bash
# Test ATR volatility assessment for XAUUSD
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    pattern_json->'volatility' as volatility_classification,
    pattern_json->'indicators'->'atr' as atr_values
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"

# Expected: ATR values for multiple timeframes with appropriate volatility classification
```

### 2. Price-Based Volatility Fallback Test
```bash
# Test price-based volatility metrics
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    pattern_json->'volatility' as volatility,
    pattern_json->'volatility_metrics'->'price_range_1h' as range_1h,
    pattern_json->'volatility_metrics'->'price_range_4h' as range_4h
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"

# Expected: Price ranges in dollars with volatility classification ending in '_price' if ATR unavailable
```

### 3. Volatility Threshold Validation
Test specific XAUUSD volatility thresholds:

**H1 ATR Thresholds:**
- High: > $15.0
- Medium: > $8.0
- Low: ≤ $8.0

**H4 ATR Thresholds:**
- High: > $25.0
- Medium: > $12.0
- Low: ≤ $12.0

**Price Range Thresholds (Fallback):**
- 4H Range High: > $20.0
- 4H Range Medium: > $10.0
- 1H Range High: > $8.0
- 1H Range Medium: > $4.0

### 4. Null Indicator Handling Test
```bash
# Test safe_float_nullable function with indicators
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    pattern_json->'indicators'->'rsi' as rsi_values,
    pattern_json->'indicators'->'ema' as ema_values,
    pattern_json->'indicators'->'atr' as atr_values
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;"

# Expected: null values preserved (not converted to 0.0)
```

## Outcome Analysis Tests

### 1. 1-Hour Outcome Calculation Test
```bash
# Test 1-hour outcome metrics
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    snapshot_time,
    pattern_json->'outcome_1h'->'max_gain_pct_1h' as max_gain,
    pattern_json->'outcome_1h'->'max_loss_pct_1h' as max_loss
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 5;"

# Expected: Percentage values for gains/losses or null if no movement
```

### 2. Trading Session Detection Test
```bash
# Test trading session classification
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    snapshot_time,
    pattern_json->'session' as trading_session,
    EXTRACT(hour FROM snapshot_time) as utc_hour
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 10;"

# Expected sessions based on UTC hour:
# 0-7: Sydney, 8-15: London, 16-23: New York
```

## Performance and Optimization Tests

### 1. JSON Size Optimization Test
```bash
# Quick table size check (FAST)
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    pg_size_pretty(pg_total_relation_size('trading_snapshots')) as table_size,
    (SELECT COUNT(*) FROM trading_snapshots WHERE symbol = 'XAUUSD' LIMIT 1000) as sample_count
"

# Measure total candles in latest pattern only (FAST)
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
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

# Expected: ~152 total candles (90%+ reduction from 1630+ full dataset)
```

### 2. Execution Time Test
```bash
# Time the pattern generation process (RUN ON HOST)
cd /home/hazem/Miando/patterns/json_split
time python3 pattern_json_live.py

# Expected: < 5 seconds for complete execution

# Container execution comparison (optional):
# time docker exec -it patterns-container python3 /app/patterns/json_split/pattern_json_live.py
```

## Data Quality Tests

### 1. Indicator Completeness Test
```bash
# Check indicator availability across timeframes
docker exec -it miando-db psql -U miando -d miando -c "
WITH latest_pattern AS (
    SELECT pattern_json
    FROM trading_snapshots 
    WHERE symbol = 'XAUUSD' 
    ORDER BY snapshot_time DESC LIMIT 1
)
SELECT 
    tf.timeframe,
    (pattern_json->'indicators'->'rsi'->tf.timeframe) IS NOT NULL as has_rsi,
    (pattern_json->'indicators'->'ema'->tf.timeframe) IS NOT NULL as has_ema,
    (pattern_json->'indicators'->'atr'->tf.timeframe) IS NOT NULL as has_atr
FROM latest_pattern, 
     (VALUES ('D1'), ('H4'), ('H1'), ('M15'), ('M5'), ('M1')) tf(timeframe);"
```

### 2. OHLC Data Integrity Test
```bash
# Verify OHLC data completeness and validity (FAST - latest pattern only)
docker exec -it miando-db psql -U miando -d miando -c "
WITH latest_pattern AS (
    SELECT pattern_json->'context'->'M1' as m1_candles
    FROM trading_snapshots 
    WHERE symbol = 'XAUUSD' 
    ORDER BY snapshot_time DESC LIMIT 1
),
candle_data AS (
    SELECT jsonb_array_elements(m1_candles) as candle
    FROM latest_pattern
)
SELECT 
    count(*) as total_candles,
    count(*) FILTER (WHERE (candle->>'open')::float > 0) as valid_open,
    count(*) FILTER (WHERE (candle->>'high')::float > 0) as valid_high,
    count(*) FILTER (WHERE (candle->>'low')::float > 0) as valid_low,
    count(*) FILTER (WHERE (candle->>'close')::float > 0) as valid_close,
    round(min((candle->>'low')::float)::numeric, 2) as min_price,
    round(max((candle->>'high')::float)::numeric, 2) as max_price
FROM candle_data;"

# Optional: Check raw OHLC data availability (can be slow)
# docker exec -it miando-db psql -U miando -d miando -c "
# SELECT timeframe, COUNT(*) FROM ohlc_data 
# WHERE symbol = 'XAUUSD' AND open_time >= NOW() - INTERVAL '24 hours'
# GROUP BY timeframe ORDER BY timeframe;"
```

## Error Handling Tests

### 1. Database Connection Failure Test
```bash
# Test with database unavailable (RUN ON HOST)
docker stop miando-db
cd /home/hazem/Miando/patterns/json_split
python3 pattern_json_live.py
# Expected: Graceful error handling with appropriate log messages

# Restart database
docker start miando-db
```

### 2. Missing Data Test
```bash
# Test with limited OHLC data (DATABASE OPERATIONS)
docker exec -it miando-db psql -U miando -d miando -c "
-- Temporarily rename table to simulate missing data
ALTER TABLE ohlc_data RENAME TO ohlc_data_backup;"

# Run pattern generation on HOST
cd /home/hazem/Miando/patterns/json_split
python3 pattern_json_live.py
# Expected: Graceful handling of missing data

# Restore table
docker exec -it miando-db psql -U miando -d miando -c "
ALTER TABLE ohlc_data_backup RENAME TO ohlc_data;"
```

## Continuous Monitoring Tests

### 1. Pattern Generation Frequency Test
```bash
# Run pattern generation multiple times to test consistency (HOST)
cd /home/hazem/Miando/patterns/json_split
for i in {1..5}; do
    echo "Test run $i:"
    python3 pattern_json_live.py
    sleep 60  # Wait 1 minute between runs
done

# Verify multiple snapshots were created (DATABASE CHECK)
docker exec -it miando-db psql -U miando -d miando -c "
SELECT count(*), 
       min(snapshot_time) as earliest, 
       max(snapshot_time) as latest
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
AND snapshot_time > NOW() - INTERVAL '10 minutes';"
```

### 2. Data Consistency Test
```bash
# Check data consistency across multiple snapshots
docker exec -it miando-db psql -U miando -d miando -c "
SELECT 
    snapshot_time,
    pattern_json->'volatility' as volatility,
    jsonb_array_length(pattern_json->'context'->'M1') as m1_candles,
    pattern_json->'session' as session
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 10;"
```

## Automated Testing Script

### Run Automated Tests (HOST)
```bash
# Execute the SUPER FAST test suite (≤5 seconds)
/home/hazem/Miando/patterns/json_split/run_super_fast_tests.sh

# Execute the comprehensive FAST test suite (≤10 seconds)
/home/hazem/Miando/patterns/json_split/run_fast_tests.sh

# Execute the full test suite (may take longer with large datasets)
/home/hazem/Miando/patterns/json_split/run_tests.sh

# Or run individual test commands:
cd /home/hazem/Miando/patterns/json_split && python3 pattern_json_live.py
```

### Container-Based Testing (Alternative)
```bash
# If testing inside container environment
docker exec -it patterns-container /app/patterns/json_split/run_tests.sh

# Or create test container with proper setup
docker run --rm -it \
  --network miando-network \
  -v /home/hazem/Miando/patterns:/app/patterns \
  -v /home/hazem/Miando/patterns/json_split/run_tests.sh:/app/run_tests.sh \
  python:3.11 bash -c "
    apt update && apt install -y python3-psycopg2 && 
    chmod +x /app/run_tests.sh && 
    /app/run_tests.sh"
```

### Create Test Runner (HOST)
```bash
# Create automated test script
cat > /home/hazem/Miando/patterns/json_split/run_tests.sh << 'EOF'
#!/bin/bash

echo "=== Pattern JSON Live System - Automated Tests ==="
echo "Started at: $(date)"

# Test 1: Basic functionality
echo "Test 1: Running pattern generation..."
cd /home/hazem/Miando/patterns/json_split
python3 pattern_json_live.py
if [ $? -eq 0 ]; then
    echo "✅ Pattern generation successful"
else
    echo "❌ Pattern generation failed"
    exit 1
fi

# Test 2: Database verification
echo "Test 2: Verifying database storage..."
RECORD_COUNT=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT COUNT(*) FROM trading_snapshots WHERE symbol = 'XAUUSD';" | tr -d ' \n\r')

if [ "$RECORD_COUNT" -gt 0 ]; then
    echo "✅ Database storage verified ($RECORD_COUNT records)"
else
    echo "❌ No records found in database"
    exit 1
fi

# Test 3: Volatility assessment
echo "Test 3: Checking volatility assessment..."
VOLATILITY=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT pattern_json->'volatility' FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" | tr -d ' \n\r"')

if [ "$VOLATILITY" != "null" ] && [ "$VOLATILITY" != "" ]; then
    echo "✅ Volatility assessment working: $VOLATILITY"
else
    echo "❌ Volatility assessment failed"
    exit 1
fi

# Test 4: Candle count optimization
echo "Test 4: Verifying candle count optimization..."
TOTAL_CANDLES=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT 
    jsonb_array_length(pattern_json->'context'->'D1') +
    jsonb_array_length(pattern_json->'context'->'H4') +
    jsonb_array_length(pattern_json->'context'->'H1') +
    jsonb_array_length(pattern_json->'context'->'M15') +
    jsonb_array_length(pattern_json->'context'->'M5') +
    jsonb_array_length(pattern_json->'context'->'M1')
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" | tr -d ' \n\r')

if [ "$TOTAL_CANDLES" -eq 152 ]; then
    echo "✅ Candle count optimization verified: $TOTAL_CANDLES candles"
else
    echo "⚠️  Candle count unexpected: $TOTAL_CANDLES (expected 152)"
fi

echo "=== All tests completed at: $(date) ==="
EOF

chmod +x /home/hazem/Miando/patterns/json_split/run_tests.sh
```

## Manual Testing Scenarios

### Scenario 1: High Volatility Period
Test during major news events or market hours when Gold volatility is typically high.

### Scenario 2: Low Volatility Period
Test during quiet market periods to verify low volatility classification.

### Scenario 3: Session Transitions
Test around UTC session transition times (8:00, 16:00) to verify session detection.

### Scenario 4: Weekend/Holiday
Test during market closure to verify graceful handling of limited data.

## Expected Results Summary

### ✅ Success Criteria
- Pattern JSON generation completes without errors
- All 6 timeframes (D1, H4, H1, M15, M5, M1) included with correct candle counts
- Volatility assessment returns meaningful classification (not "unknown")
- Price-based fallback works when ATR unavailable
- 1-hour outcome calculations complete
- Trading session detected correctly
- Total candle count ~152 (90%+ optimization achieved)
- Database storage successful with valid JSONB structure

### ⚠️ Warning Indicators
- Volatility returns "no_data" consistently
- Missing indicators for multiple timeframes
- Execution time > 5 seconds
- Database connection timeouts

### ❌ Failure Criteria
- Script crashes or exits with error
- No data stored in trading_snapshots table
- Volatility permanently "unknown"
- Missing critical timeframes
- Invalid OHLC data (zero/negative prices)

## Troubleshooting Guide

### Issue: "ModuleNotFoundError: No module named 'psycopg2'"
**Solution (Host)**: Install system package: `sudo apt install python3-psycopg2`
**Solution (Container)**: Install in container: `apt update && apt install python3-psycopg2`

### Issue: "Volatility: unknown"
**Solution**: Check ATR indicator availability and verify price-based fallback metrics.

### Issue: Missing candle data
**Solution**: Verify OHLC data availability for XAUUSD across all timeframes.

### Issue: Database connection errors
**Solution**: 
- **Host**: Verify Docker containers running and database credentials
- **Container**: Ensure container is on correct network (`--network miando-network`)

### Issue: File not found errors
**Solution**:
- **Host**: Verify correct working directory: `/home/hazem/Miando/patterns/json_split/`
- **Container**: Check volume mounting and file paths (`/app/patterns/json_split/`)

### Issue: Slow execution
**Solution**: Check database performance and optimize queries if needed.

### Issue: Container connectivity problems
**Solution**:
- Verify container network: `docker network ls | grep miando`
- Check container can reach database: `docker exec -it patterns-container ping miando-db`
- Ensure proper volume mounting: `-v /home/hazem/Miando/patterns:/app/patterns`

## Production Deployment Checklist

- [ ] All tests passing successfully
- [ ] Volatility assessment working with price fallback
- [ ] Candle count optimization verified (152 total)
- [ ] Database storage functioning correctly
- [ ] Error handling tested and working
- [ ] Automated testing script created
- [ ] Monitoring and alerting configured
- [ ] Documentation updated and complete

---

**Last Updated**: August 8, 2025  
**System Version**: Pattern JSON Live v2.0 with Enhanced Volatility Assessment  
**Target Symbol**: XAUUSD (Gold)  
**Optimization**: 90%+ data reduction (152 vs 1630+ candles)
