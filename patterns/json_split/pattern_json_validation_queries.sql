-- CORRECTED SQL QUERIES FOR PATTERN JSON SYSTEM
-- (Replace 'market_state_json' with 'pattern_json')

-- 1. MAIN QUERY: View formatted Pattern JSON
SELECT jsonb_pretty(pattern_json)
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 1;

-- 2. VALIDATION CHECKLIST QUERIES:

-- Check Volatility vs ATR Rule
SELECT 
    symbol,
    snapshot_time,
    pattern_json->>'volatility' as volatility_level,
    pattern_json->'indicators'->'atr'->>'H1' as atr_h1_value,
    CASE 
        WHEN (pattern_json->'indicators'->'atr'->>'H1')::float > 5.0 
        THEN 'Should be high_price'
        ELSE 'Should be medium/low_price'
    END as expected_volatility
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 3;

-- Check Session vs UTC Hour Rules
SELECT 
    symbol,
    snapshot_time,
    EXTRACT(hour FROM snapshot_time) as utc_hour,
    pattern_json->>'session' as current_session,
    CASE 
        WHEN EXTRACT(hour FROM snapshot_time) BETWEEN 0 AND 6 THEN 'Sydney'
        WHEN EXTRACT(hour FROM snapshot_time) BETWEEN 7 AND 14 THEN 'London'
        WHEN EXTRACT(hour FROM snapshot_time) BETWEEN 15 AND 21 THEN 'New York'
        ELSE 'Sydney'
    END as expected_session
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 3;

-- Check Outcome Predictions
SELECT 
    symbol,
    snapshot_time,
    pattern_json->'outcome_1h'->>'max_gain_pct_1h' as max_gain_prediction,
    pattern_json->'outcome_1h'->>'max_loss_pct_1h' as max_loss_prediction,
    pattern_json->>'volatility' as volatility_level
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 5;

-- Check Data Optimization (Candle Counts)
SELECT 
    symbol,
    snapshot_time,
    jsonb_array_length(pattern_json->'context'->'M1') as M1_candles,
    jsonb_array_length(pattern_json->'context'->'M5') as M5_candles,
    jsonb_array_length(pattern_json->'context'->'M15') as M15_candles,
    jsonb_array_length(pattern_json->'context'->'H1') as H1_candles,
    jsonb_array_length(pattern_json->'context'->'H4') as H4_candles,
    jsonb_array_length(pattern_json->'context'->'D1') as D1_candles,
    (
        COALESCE(jsonb_array_length(pattern_json->'context'->'M1'), 0) +
        COALESCE(jsonb_array_length(pattern_json->'context'->'M5'), 0) +
        COALESCE(jsonb_array_length(pattern_json->'context'->'M15'), 0) +
        COALESCE(jsonb_array_length(pattern_json->'context'->'H1'), 0) +
        COALESCE(jsonb_array_length(pattern_json->'context'->'H4'), 0) +
        COALESCE(jsonb_array_length(pattern_json->'context'->'D1'), 0)
    ) as total_candles
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 3;

-- Check JSON Structure and Keys
SELECT 
    symbol,
    snapshot_time,
    jsonb_object_keys(pattern_json) as top_level_keys
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 1;

-- Summary Status Check
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN pattern_json IS NOT NULL THEN 1 END) as records_with_pattern_json,
    MAX(snapshot_time) as latest_snapshot,
    MIN(snapshot_time) as earliest_snapshot
FROM trading_snapshots
WHERE symbol = 'XAUUSD';
