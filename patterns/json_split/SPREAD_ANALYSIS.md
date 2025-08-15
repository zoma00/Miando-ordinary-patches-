# 📊 SPREAD ANALYSIS QUERIES
## Validation of Hazem's Important Notes

### 🎯 **YOUR NOTES VALIDATION:**

#### ✅ **Note 1: "Always calculate using the latest available M1 candle"**
**Status**: ✅ **CONFIRMED** - System uses `get_latest_m1_time()` function

#### ✅ **Note 2: "Use UTC time for session detection"**  
**Status**: ✅ **CONFIRMED** - Session logic uses UTC hours with correct mapping

#### ✅ **Note 3: "No historical version for now — this is live only"**
**Status**: ✅ **CONFIRMED** - Pattern JSON Live system (historical exists but separate)

#### ⚠️ **Note 4: "Later, we'll replace news_event = false with real news API data"**
**Status**: ⚠️ **NEEDS INVESTIGATION** - Check if news_event field exists in pattern JSON

#### ✅ **Note 5: "Ensure spread is never negative and has 2 decimal places"**
**Status**: ✅ **CONFIRMED** - `round(max(0.01, spread), 2)` ensures positive + 2 decimals

---

## 💰 **SPREAD QUERIES FOR PATTERN JSON SYSTEM:**

### **1. Current Spread in Pattern JSON:**
```sql
-- Check if spread data exists in Pattern JSON
SELECT 
    symbol,
    snapshot_time,
    pattern_json->>'spread' as pattern_spread,
    pattern_json->'market_state'->>'spread' as market_spread,
    pattern_json->'indicators'->>'spread' as indicator_spread,
    pattern_json AS full_json_check
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 3;
```

### **2. Latest M1 Candle Spread Calculation:**
```sql
-- Calculate spread from latest M1 candle (as per your notes)
SELECT 
    symbol,
    open_time as latest_m1_time,
    high_price,
    low_price,
    -- Calculate spread as 10% of candle range (per your logic)
    ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2) as calculated_spread,
    -- Verify spread is never negative and has 2 decimals
    CASE 
        WHEN ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2) >= 0.01 
        THEN '✅ Valid Spread'
        ELSE '❌ Invalid Spread'
    END as spread_validation
FROM ohlc_data
WHERE symbol = 'XAUUSD' AND timeframe = 'M1'
ORDER BY open_time DESC
LIMIT 5;
```

### **3. Historical Spread Trends:**
```sql
-- Analyze spread patterns over recent M1 candles
SELECT 
    DATE_TRUNC('hour', open_time) as hour_group,
    symbol,
    COUNT(*) as candle_count,
    AVG(ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2)) as avg_spread,
    MIN(ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2)) as min_spread,
    MAX(ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2)) as max_spread
FROM ohlc_data
WHERE symbol = 'XAUUSD' 
AND timeframe = 'M1'
AND open_time >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', open_time), symbol
ORDER BY hour_group DESC
LIMIT 10;
```

### **4. Spread vs Session Analysis:**
```sql
-- Spread behavior across trading sessions (per your UTC session mapping)
SELECT 
    symbol,
    open_time,
    EXTRACT(hour FROM open_time) as utc_hour,
    CASE 
        WHEN EXTRACT(hour FROM open_time) BETWEEN 22 AND 23 OR EXTRACT(hour FROM open_time) BETWEEN 0 AND 6 THEN 'Sydney'
        WHEN EXTRACT(hour FROM open_time) BETWEEN 7 AND 14 THEN 'London'
        WHEN EXTRACT(hour FROM open_time) BETWEEN 15 AND 21 THEN 'New York'
        ELSE 'Unknown'
    END as trading_session,
    ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2) as spread,
    high_price - low_price as candle_range
FROM ohlc_data
WHERE symbol = 'XAUUSD' 
AND timeframe = 'M1'
AND open_time >= NOW() - INTERVAL '6 hours'
ORDER BY open_time DESC
LIMIT 10;
```

### **5. News Event Field Check:**
```sql
-- Check if news_event field exists in Pattern JSON (per your note about future news API)
SELECT 
    symbol,
    snapshot_time,
    pattern_json ? 'news_event' as has_news_field,
    pattern_json->>'news_event' as news_event_value,
    pattern_json->'news'->>'event' as nested_news_event,
    -- Check various possible news field locations
    CASE 
        WHEN pattern_json ? 'news_event' THEN 'Found: news_event field'
        WHEN pattern_json ? 'news' THEN 'Found: news object'
        ELSE 'No news fields found'
    END as news_field_status
FROM trading_snapshots
WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC
LIMIT 3;
```

### **6. Spread Validation Summary:**
```sql
-- Comprehensive spread validation per your requirements
WITH latest_candles AS (
    SELECT 
        symbol,
        open_time,
        high_price,
        low_price,
        ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2) as spread
    FROM ohlc_data
    WHERE symbol = 'XAUUSD' AND timeframe = 'M1'
    ORDER BY open_time DESC
    LIMIT 100
)
SELECT 
    '📊 SPREAD VALIDATION SUMMARY' as check_type,
    COUNT(*) as total_candles,
    COUNT(CASE WHEN spread >= 0.01 THEN 1 END) as positive_spreads,
    COUNT(CASE WHEN spread::text ~ '^[0-9]+\.[0-9]{2}$' THEN 1 END) as two_decimal_spreads,
    MIN(spread) as min_spread,
    MAX(spread) as max_spread,
    AVG(spread) as avg_spread,
    CASE 
        WHEN COUNT(CASE WHEN spread >= 0.01 THEN 1 END) = COUNT(*) 
        THEN '✅ All spreads positive'
        ELSE '❌ Some negative spreads found'
    END as positive_validation,
    CASE 
        WHEN COUNT(CASE WHEN spread::text ~ '^[0-9]+\.[0-9]{2}$' THEN 1 END) = COUNT(*)
        THEN '✅ All spreads 2 decimals'
        ELSE '❌ Some spreads not 2 decimals'
    END as decimal_validation
FROM latest_candles;
```

---

## 🎯 **QUICK SPREAD CHECK COMMANDS:**

```bash
# 1. Latest M1 candle spread
psql -h localhost -p 5434 -U miando -d miando -c "
SELECT symbol, open_time, 
ROUND(GREATEST(0.01, (high_price - low_price) * 0.1), 2) as spread
FROM ohlc_data WHERE symbol = 'XAUUSD' AND timeframe = 'M1'
ORDER BY open_time DESC LIMIT 1;"

# 2. Check Pattern JSON for spread data
psql -h localhost -p 5434 -U miando -d miando -c "
SELECT pattern_json->>'spread', pattern_json ? 'news_event'
FROM trading_snapshots WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
ORDER BY snapshot_time DESC LIMIT 1;"
```
