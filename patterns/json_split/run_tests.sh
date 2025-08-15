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

# Test 2: Database verification (optimized with LIMIT)
echo "Test 2: Verifying database storage..."
RECORD_COUNT=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT COUNT(*) FROM (
    SELECT 1 FROM trading_snapshots 
    WHERE symbol = 'XAUUSD' 
    LIMIT 100
) as limited;" | tr -d ' \n\r')

if [ "$RECORD_COUNT" -gt 0 ]; then
    echo "✅ Database storage verified ($RECORD_COUNT records found, limited check)"
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

# Test 5: Enhanced volatility metrics
echo "Test 5: Checking enhanced volatility metrics..."
PRICE_METRICS=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT pattern_json->'volatility_metrics' FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;")

if [[ "$PRICE_METRICS" != "null" ]] && [[ "$PRICE_METRICS" != "" ]]; then
    echo "✅ Enhanced volatility metrics available"
    echo "   Metrics: $PRICE_METRICS"
else
    echo "⚠️  Enhanced volatility metrics missing"
fi

# Test 6: Indicator data quality
echo "Test 6: Checking indicator data quality..."
INDICATOR_STATUS=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT 
    CASE 
        WHEN pattern_json->'indicators'->'atr' IS NOT NULL THEN 'ATR_OK'
        ELSE 'ATR_MISSING'
    END ||
    CASE 
        WHEN pattern_json->'indicators'->'rsi' IS NOT NULL THEN ',RSI_OK'
        ELSE ',RSI_MISSING'
    END ||
    CASE 
        WHEN pattern_json->'indicators'->'ema' IS NOT NULL THEN ',EMA_OK'
        ELSE ',EMA_MISSING'
    END as status
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" | tr -d ' \n\r')

echo "   Indicator Status: $INDICATOR_STATUS"

# Test 7: Session detection
echo "Test 7: Verifying session detection..."
SESSION=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT pattern_json->'session' FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" | tr -d ' \n\r"')

if [[ "$SESSION" =~ ^\"(Sydney|London|New\ York)\"$ ]]; then
    echo "✅ Session detection working: $SESSION"
else
    echo "⚠️  Session detection issue: $SESSION"
fi

# Test 8: Outcome calculation
echo "Test 8: Checking 1-hour outcome calculation..."
OUTCOME=$(docker exec -it miando-db psql -U miando -d miando -t -c "
SELECT pattern_json->'outcome_1h' FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;")

if [[ "$OUTCOME" != "null" ]] && [[ "$OUTCOME" != "" ]]; then
    echo "✅ 1-hour outcome calculation available"
else
    echo "⚠️  1-hour outcome calculation missing"
fi

echo ""
echo "=== Test Summary ==="
echo "✅ = Pass, ⚠️ = Warning, ❌ = Fail"
echo "=== All tests completed at: $(date) ==="
