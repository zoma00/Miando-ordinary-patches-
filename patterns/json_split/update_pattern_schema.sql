-- Update schema for Pattern JSON optimization
-- Add pattern_json column to trading_snapshots table

-- Add new column for optimized pattern JSON
ALTER TABLE trading_snapshots 
ADD COLUMN IF NOT EXISTS pattern_json JSONB;

-- Create index for pattern JSON queries
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_pattern_json 
ON trading_snapshots USING GIN (pattern_json);

-- Create index for pattern JSON metadata queries
CREATE INDEX IF NOT EXISTS idx_trading_snapshots_pattern_symbol_time 
ON trading_snapshots (symbol, snapshot_time) 
WHERE pattern_json IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN trading_snapshots.pattern_json IS 'Optimized compact JSON for pattern matching and vectorization';

-- Example query to validate pattern JSON structure
/*
SELECT 
    symbol,
    snapshot_time,
    pattern_json->>'volatility' as volatility,
    pattern_json->>'session' as session,
    pattern_json->'outcome_1h'->>'max_gain_pct_1h' as max_gain_1h,
    jsonb_array_length(pattern_json->'context'->'M1') as m1_candles,
    jsonb_array_length(pattern_json->'context'->'H1') as h1_candles
FROM trading_snapshots 
WHERE pattern_json IS NOT NULL 
ORDER BY snapshot_time DESC 
LIMIT 5;
*/
