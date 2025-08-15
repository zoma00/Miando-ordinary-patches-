#!/bin/bash

echo "=== Pattern JSON Live System - FAST Tests ==="
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

# Test 2: Ultra-fast database verification
echo "Test 2: Ultra-fast database verification..."
PATTERN_EXISTS=$(docker exec miando-db psql -U miando -d miando -t -A -c "
SELECT 1 FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
LIMIT 1;" 2>/dev/null | head -1)

if [ "$PATTERN_EXISTS" = "1" ]; then
    echo "✅ Database storage verified (pattern exists)"
else
    echo "❌ No patterns found in database"
    exit 1
fi

# Test 3: Ultra-fast volatility check
echo "Test 3: Checking volatility assessment..."
VOLATILITY=$(docker exec miando-db psql -U miando -d miando -t -A -c "
SELECT pattern_json->'volatility' FROM trading_snapshots 
WHERE symbol = 'XAUUSD' 
ORDER BY snapshot_time DESC LIMIT 1;" 2>/dev/null | head -1 | tr -d '"')

if [ "$VOLATILITY" != "null" ] && [ "$VOLATILITY" != "" ]; then
    echo "✅ Volatility assessment working: $VOLATILITY"
else
    echo "❌ Volatility assessment failed"
    exit 1
fi

# Test 4: Ultra-fast candle count check
echo "Test 4: Verifying candle count optimization..."
TOTAL_CANDLES=$(docker exec miando-db psql -U miando -d miando -t -A -c "
SELECT 
    jsonb_array_length(pattern_json->'context'->'D1') +
    jsonb_array_length(pattern_json->'context'->'H4') +
    jsonb_array_length(pattern_json->'context'->'H1') +
    jsonb_array_length(pattern_json->'context'->'M15') +
    jsonb_array_length(pattern_json->'context'->'M5') +
    jsonb_array_length(pattern_json->'context'->'M1')
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" 2>/dev/null | head -1)

if [ "$TOTAL_CANDLES" = "152" ]; then
    echo "✅ Candle count optimization verified: $TOTAL_CANDLES candles"
else
    echo "⚠️  Candle count unexpected: $TOTAL_CANDLES (expected 152)"
fi

# Test 5: Ultra-fast volatility metrics check
echo "Test 5: Checking enhanced volatility metrics..."
PRICE_METRICS=$(docker exec miando-db psql -U miando -d miando -t -A -c "
SELECT CASE WHEN pattern_json ? 'volatility_metrics' 
THEN 'available' ELSE 'missing' END 
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" 2>/dev/null | head -1)

if [ "$PRICE_METRICS" = "available" ]; then
    echo "✅ Enhanced volatility metrics available"
else
    echo "⚠️  Enhanced volatility metrics missing"
fi

# Test 6: Ultra-fast JSON size check
echo "Test 6: Checking JSON size efficiency..."
JSON_SIZE=$(docker exec miando-db psql -U miando -d miando -t -A -c "
SELECT length(pattern_json::text) 
FROM trading_snapshots 
WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" 2>/dev/null | head -1)

if [ ! -z "$JSON_SIZE" ] && [ "$JSON_SIZE" -lt 50000 ]; then  # Less than 50KB
    echo "✅ JSON size optimized: ${JSON_SIZE} bytes"
else
    echo "⚠️  JSON size: ${JSON_SIZE} bytes"
fi

echo ""
echo "=== Fast Test Summary ==="
echo "✅ = Pass, ⚠️ = Warning, ❌ = Fail"
echo "All tests completed in seconds (optimized for speed)"
echo "=== Tests completed at: $(date) ==="
