-- OHLC Data Truncation Queries
-- Use these SQL commands to truncate the ohlc_data table

-- ===========================================
-- 1. CHECK CURRENT DATA (before truncating)
-- ===========================================

-- Total record count
SELECT COUNT(*) as total_records FROM ohlc_data;

-- Records by symbol
SELECT symbol, COUNT(*) as count 
FROM ohlc_data 
GROUP BY symbol 
ORDER BY count DESC;

-- Records by timeframe
SELECT timeframe, COUNT(*) as count 
FROM ohlc_data 
GROUP BY timeframe 
ORDER BY count DESC;

-- Date range
SELECT 
    MIN(open_time) as earliest_date,
    MAX(open_time) as latest_date,
    COUNT(*) as total_records
FROM ohlc_data;

-- ===========================================
-- 2. TRUNCATE THE TABLE (removes ALL data)
-- ===========================================

-- WARNING: This will delete ALL data from ohlc_data table!
-- TRUNCATE is faster than DELETE and resets auto-increment counters
TRUNCATE TABLE ohlc_data RESTART IDENTITY;

-- Alternative: DELETE all records (slower but more standard)
-- DELETE FROM ohlc_data;

-- ===========================================
-- 3. VERIFY TRUNCATION
-- ===========================================

-- Check that table is empty
SELECT COUNT(*) as remaining_records FROM ohlc_data;

-- ===========================================
-- 4. SELECTIVE DELETION (if you don't want to truncate everything)
-- ===========================================

-- Delete specific symbol data
-- DELETE FROM ohlc_data WHERE symbol = 'XAUUSD';

-- Delete specific timeframe data
-- DELETE FROM ohlc_data WHERE timeframe = 'M1';

-- Delete data older than a specific date
-- DELETE FROM ohlc_data WHERE open_time < '2025-08-01';

-- Delete data for specific symbol and timeframe
-- DELETE FROM ohlc_data WHERE symbol = 'EURUSD' AND timeframe = 'M1';

-- ===========================================
-- 5. RESET AUTO-INCREMENT (if using DELETE instead of TRUNCATE)
-- ===========================================

-- If you used DELETE instead of TRUNCATE, reset the sequence
-- ALTER SEQUENCE ohlc_data_id_seq RESTART WITH 1;
