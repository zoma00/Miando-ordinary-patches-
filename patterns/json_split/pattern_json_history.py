#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pattern JSON Historical Exporter - Optimized Feature 2
Generates compact historical pattern snapshots optimized for vector matching.

This script:
1. Processes all historical M1 timestamps
2. Builds compact pattern JSON for each timestamp
3. Includes 1-hour outcomes for pattern evaluation
4. Stores in trading_snapshots.pattern_json column
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

from common import (
    get_cursor, format_timestamp_utc, safe_float, safe_int,
    log_info, log_error, log_success, SYMBOL
)

# Import from live version
from pattern_json_live import (
    PATTERN_TIMEFRAME_LIMITS, KEY_INDICATORS,
    get_trading_session, assess_volatility
)


def get_all_historical_m1_timestamps(symbol: str, start_date: Optional[datetime] = None, 
                                   end_date: Optional[datetime] = None) -> List[datetime]:
    """
    Get all historical M1 timestamps for processing.
    """
    timestamps = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            query = """
                SELECT DISTINCT open_time
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1'
            """
            params = [symbol]
            
            if start_date:
                query += " AND open_time >= %s"
                params.append(start_date)
                
            if end_date:
                query += " AND open_time <= %s"
                params.append(end_date)
                
            query += " ORDER BY open_time ASC"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            timestamps = [row['open_time'] for row in rows]
            
        log_info(f"Found {len(timestamps)} historical M1 timestamps")
        
    except Exception as e:
        log_error(f"Failed to get historical timestamps: {e}")
        
    return timestamps


def fetch_historical_pattern_candles(symbol: str, timeframe: str, limit: int, 
                                   up_to_time: datetime) -> List[Dict[str, Any]]:
    """
    Fetch historical candles available up to a specific timestamp.
    Only includes candles that would have been available at that point in time.
    """
    candles = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT 
                    open_time, open_price, high_price, low_price, close_price, volume,
                    rsi, ema, atr, bb_middle, bb_upper, bb_lower
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = %s AND open_time <= %s
                ORDER BY open_time DESC
                LIMIT %s
            """, (symbol, timeframe, up_to_time, limit))
            
            rows = cur.fetchall()
            
            # Convert to compact structure, sorted oldest first
            for row in reversed(rows):
                candle = {
                    "open_time": format_timestamp_utc(row["open_time"]),
                    "open": safe_float(row["open_price"]),
                    "high": safe_float(row["high_price"]),
                    "low": safe_float(row["low_price"]),
                    "close": safe_float(row["close_price"]),
                    "volume": safe_int(row["volume"]),
                    # Key indicators only
                    "rsi": safe_float(row["rsi"]),
                    "ema": safe_float(row["ema"]),
                    "atr": safe_float(row["atr"]),
                    "bb_middle": safe_float(row["bb_middle"]),
                    "bb_upper": safe_float(row["bb_upper"]),
                    "bb_lower": safe_float(row["bb_lower"]),
                }
                candles.append(candle)
                
    except Exception as e:
        log_error(f"Failed to fetch historical {timeframe} data: {e}")
        
    return candles


def get_historical_indicator_values(symbol: str, up_to_time: datetime) -> Dict[str, Dict[str, float]]:
    """
    Get historical indicator values for all timeframes up to a specific time.
    """
    indicators = {}
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            for timeframe in PATTERN_TIMEFRAME_LIMITS.keys():
                cur.execute("""
                    SELECT rsi, ema, atr
                    FROM ohlc_data
                    WHERE symbol = %s AND timeframe = %s AND open_time <= %s
                    ORDER BY open_time DESC
                    LIMIT 1
                """, (symbol, timeframe, up_to_time))
                
                row = cur.fetchone()
                if row:
                    if 'rsi' not in indicators:
                        indicators['rsi'] = {}
                    if 'ema' not in indicators:
                        indicators['ema'] = {}
                    if 'atr' not in indicators:
                        indicators['atr'] = {}
                        
                    indicators['rsi'][timeframe] = safe_float(row['rsi'])
                    indicators['ema'][timeframe] = safe_float(row['ema'])
                    indicators['atr'][timeframe] = safe_float(row['atr'])
                    
    except Exception as e:
        log_error(f"Failed to get historical indicator values: {e}")
        
    return indicators


def calculate_historical_1h_outcome(symbol: str, snapshot_time: datetime) -> Dict[str, float]:
    """
    Calculate historical 1-hour outcome from snapshot time.
    """
    outcome = {
        "max_gain_pct_1h": None,
        "max_loss_pct_1h": None
    }
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get price at snapshot time
            cur.execute("""
                SELECT close_price
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1' 
                AND open_time = %s
            """, (symbol, snapshot_time))
            
            current_row = cur.fetchone()
            if not current_row:
                return outcome
                
            current_price = safe_float(current_row['close_price'])
            if current_price == 0.0:
                return outcome
            
            # Get all M1 candles in the next hour
            end_time = snapshot_time + timedelta(hours=1)
            cur.execute("""
                SELECT high_price, low_price
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1'
                AND open_time > %s AND open_time <= %s
                ORDER BY open_time ASC
            """, (symbol, snapshot_time, end_time))
            
            rows = cur.fetchall()
            if not rows:
                return outcome
            
            max_high = max(safe_float(row['high_price']) for row in rows)
            min_low = min(safe_float(row['low_price']) for row in rows)
            
            # Calculate percentage gains/losses
            if max_high > current_price:
                outcome["max_gain_pct_1h"] = round(((max_high - current_price) / current_price) * 100, 2)
            
            if min_low < current_price:
                outcome["max_loss_pct_1h"] = round(((min_low - current_price) / current_price) * 100, 2)
                
    except Exception as e:
        log_error(f"Failed to calculate historical 1h outcome: {e}")
        
    return outcome


def build_historical_pattern_json(symbol: str, snapshot_time: datetime) -> Optional[Dict[str, Any]]:
    """
    Build historical pattern JSON for a specific timestamp.
    """
    try:
        log_info(f"Building historical pattern JSON for {symbol} at {snapshot_time}")
        
        # Fetch historical candle data for all timeframes
        context = {}
        for timeframe, limit in PATTERN_TIMEFRAME_LIMITS.items():
            candles = fetch_historical_pattern_candles(symbol, timeframe, limit, snapshot_time)
            context[timeframe] = candles
            
        # Get historical indicator values
        indicators = get_historical_indicator_values(symbol, snapshot_time)
        
        # Calculate 1-hour outcome
        outcome_1h = calculate_historical_1h_outcome(symbol, snapshot_time)
        
        # Determine session and volatility
        session = get_trading_session(snapshot_time)
        volatility = assess_volatility(indicators.get('atr', {}))
        
        # Build compact pattern JSON
        pattern_json = {
            "symbol": symbol,
            "snapshot_time": format_timestamp_utc(snapshot_time),
            "context": context,
            "indicators": indicators,
            "outcome_1h": outcome_1h,
            "session": session,
            "volatility": volatility
        }
        
        return pattern_json
        
    except Exception as e:
        log_error(f"Failed to build historical pattern JSON: {e}")
        return None


def store_historical_pattern_json(symbol: str, snapshot_time: datetime, 
                                pattern_json: Dict[str, Any]) -> bool:
    """
    Store historical pattern JSON in database.
    """
    import json
    try:
        with get_cursor() as cur:
            # Insert pattern JSON (ignore if already exists)
            cur.execute("""
                INSERT INTO trading_snapshots (symbol, snapshot_time, snapshot_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (symbol, snapshot_time) DO NOTHING
            """, (symbol, snapshot_time, json.dumps(pattern_json)))
        return True
    except Exception as e:
        log_error(f"Failed to store historical pattern JSON: {e}")
        return False


def process_historical_batch(symbol: str, timestamps: List[datetime], 
                           batch_size: int = 1000) -> Tuple[int, int]:
    """
    Process historical timestamps in batches.
    Returns (successful, failed) counts.
    """
    successful = 0
    failed = 0
    
    for i in range(0, len(timestamps), batch_size):
        batch = timestamps[i:i + batch_size]
        batch_start = i + 1
        batch_end = min(i + batch_size, len(timestamps))
        
        log_info(f"Processing batch {batch_start}-{batch_end} of {len(timestamps)}")
        
        for timestamp in batch:
            try:
                # Build pattern JSON
                pattern_json = build_historical_pattern_json(symbol, timestamp)
                if not pattern_json:
                    log_error(f"Pattern JSON is None for {symbol} at {timestamp}, skipping insert.")
                    failed += 1
                    continue
                    
                # Store in database
                success = store_historical_pattern_json(symbol, timestamp, pattern_json)
                if success:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                log_error(f"Failed to process timestamp {timestamp}: {e}")
                failed += 1
        
        # Log batch progress
        log_info(f"Batch complete: {successful} successful, {failed} failed")
        
        # Small delay between batches to avoid overwhelming the database
        time.sleep(0.1)
    
    return successful, failed


def main(start_date: Optional[str] = None, end_date: Optional[str] = None, 
         batch_size: int = 1000):
    """
    Main execution function for historical pattern JSON generation.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        batch_size: Number of timestamps to process per batch
    """
    log_info("Starting Historical Pattern JSON Export...")
    
    try:
        # Parse date parameters
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        # Get all distinct symbols from ohlc_data
        symbols = []
        try:
            from common import get_cursor
            with get_cursor(dict_cursor=True) as cur:
                cur.execute("SELECT DISTINCT symbol FROM ohlc_data")
                rows = cur.fetchall()
                symbols = [row['symbol'] for row in rows]
        except Exception as e:
            log_error(f"Failed to get symbols: {e}")
            return

        for symbol in symbols:
            log_info(f"Processing symbol: {symbol}")
            timestamps = get_all_historical_m1_timestamps(symbol, start_dt, end_dt)
            if not timestamps:
                log_error(f"No historical timestamps found for {symbol}")
                continue
            log_info(f"Processing {len(timestamps)} historical timestamps for {symbol}")
            successful, failed = process_historical_batch(symbol, timestamps, batch_size)
            log_success(f"{symbol}: {successful} successful, {failed} failed")
    except Exception as e:
        log_error(f"Historical pattern JSON export error: {e}")


if __name__ == "__main__":
    import sys
    
    # Command line arguments
    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    
    main(start_date, end_date, batch_size)
