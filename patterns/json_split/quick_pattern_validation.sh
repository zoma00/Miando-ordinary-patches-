#!/bin/bash

echo "🔍 Pattern JSON Quick Validation"
echo "=================================="

# Read the database password from the environment (see .env.example)
export PGPASSWORD="${PGPASSWORD:?Set PGPASSWORD before running (see .env.example)}"

echo "1. Checking Pattern JSON data structure..."
psql -h localhost -p 5434 -U miando -d miando -c "
SELECT 
    symbol,
    snapshot_time,
    pattern_json->>'volatility' as volatility,
    pattern_json->'indicators' ? 'atr' as has_atr,
    pattern_json->'outcome_1h' ? 'max_gain_pct_1h' as has_predictions,
    pattern_json->>'session' as session,
    EXTRACT(hour FROM snapshot_time) as utc_hour
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 3;
"

echo ""
echo "2. Checking ATR indicator details..."
psql -h localhost -p 5434 -U miando -d miando -c "
SELECT 
    pattern_json->'indicators' as all_indicators
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 1;
"

echo ""
echo "3. Session mapping validation..."
echo "Expected sessions:"
echo "  Hours 22-06: Sydney"
echo "  Hours 07-14: London" 
echo "  Hours 15-21: New York"

echo ""
echo "✅ Validation complete! Check results above."
