# Pattern JSON Optimization System

## Overview
The Pattern JSON system provides optimized, compact data structures for vector matching and trading pattern analysis.

## Key Features
- **90%+ Size Reduction**: From 1630+ candles to 152 maximum candles
- **Vector-Ready Structure**: Optimized for machine learning and pattern matching
- **Real-time Export**: Live pattern JSON generation with 1-hour outcomes
- **Historical Processing**: Complete historical pattern analysis
- **Database Integration**: JSONB storage with GIN indexing

## Pattern Limits (Optimized)
- **D1**: 7 candles (1 week)
- **H4**: 5 candles (1 day)  
- **H1**: 20 candles (20 hours)
- **M15**: 30 candles (7.5 hours)
- **M5**: 30 candles (2.5 hours)
- **M1**: 60 candles (1 hour)
- **Total**: 152 candles maximum

## Structure
```json
{
  "symbol": "XAUUSD",
  "snapshot_time": "2025-01-09T12:00:00Z",
  "context": {
    "D1": [...], "H4": [...], "H1": [...],
    "M15": [...], "M5": [...], "M1": [...]
  },
  "indicators": {
    "rsi": {"D1": 65.5, "H4": 62.1, ...},
    "ema": {"D1": 2350.0, "H4": 2348.5, ...},
    "atr": {"D1": 15.2, "H4": 8.7, ...}
  },
  "outcome_1h": {
    "max_gain_pct_1h": 0.15,
    "max_loss_pct_1h": -0.08
  },
  "metadata": {
    "volatility": "medium",
    "session": "london",
    "total_candles": 152
  }
}
```

## Usage

### Live Export
```bash
cd /home/hazem/Miando/patterns/json_split
python pattern_json_live.py
```

### Historical Processing
```bash
cd /home/hazem/Miando/patterns/json_split
python pattern_json_history.py
```

### Database Queries
```sql
-- Get recent patterns with high gains
SELECT symbol, snapshot_time, 
       pattern_json->>'volatility' as volatility,
       pattern_json->'outcome_1h'->>'max_gain_pct_1h' as max_gain_1h
FROM trading_snapshots 
WHERE pattern_json->'outcome_1h'->>'max_gain_pct_1h'::float > 0.1
ORDER BY snapshot_time DESC;

-- Count candles by timeframe
SELECT 
    jsonb_array_length(pattern_json->'context'->'M1') as m1_candles,
    jsonb_array_length(pattern_json->'context'->'H1') as h1_candles,
    jsonb_array_length(pattern_json->'context'->'D1') as d1_candles
FROM trading_snapshots 
WHERE pattern_json IS NOT NULL;
```

## Vector Matching Ready
The Pattern JSON structure is optimized for:
- Machine learning feature extraction
- Vector similarity calculations
- Pattern recognition algorithms
- Trading signal generation

## Performance
- Database queries: < 100ms with GIN indexing
- Export processing: ~2-3 seconds per symbol
- Size efficiency: 90%+ reduction vs full OHLC
- Memory usage: Minimal due to compact structure
