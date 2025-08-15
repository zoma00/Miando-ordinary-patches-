#!/bin/bash

echo "=== SUPER FAST Pattern JSON Test ==="
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

# Test 2: Lightning-fast existence check
echo "Test 2: Quick existence check..."
EXISTS=$(docker exec miando-db psql -U miando -d miando -t -A -c "SELECT 1 FROM trading_snapshots WHERE symbol = 'XAUUSD' LIMIT 1;" 2>/dev/null)
if [ "$EXISTS" = "1" ]; then
    echo "✅ Database verified"
else
    echo "❌ No data found"
    exit 1
fi

# Test 3: Quick volatility check
echo "Test 3: Volatility check..."
VOL=$(docker exec miando-db psql -U miando -d miando -t -A -c "SELECT pattern_json->'volatility' FROM trading_snapshots WHERE symbol = 'XAUUSD' ORDER BY snapshot_time DESC LIMIT 1;" 2>/dev/null | head -1)
if [ ! -z "$VOL" ] && [ "$VOL" != "null" ]; then
    echo "✅ Volatility: $(echo $VOL | tr -d '"')"
else
    echo "❌ Volatility failed"
    exit 1
fi

echo ""
echo "=== SUPER FAST Test Summary ==="
echo "✅ All critical tests passed in seconds!"
echo "=== Completed at: $(date) ==="
