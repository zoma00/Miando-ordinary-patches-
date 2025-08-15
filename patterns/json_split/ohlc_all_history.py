#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OHLC All Historical Exporter - Feature 2
Generates historical snapshots (ohlc_all.json) from existing OHLC data.

This script:
1. Retrieves all historical M1 timestamps
2. For each M1 timestamp, builds a snapshot with available candles at that time
3. Stores historical snapshots in trading_snapshots.ohlc_all_json column
4. Processes in batches to avoid database overload
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from common import (
    get_cursor, insert_snapshot, format_timestamp_utc, 
    safe_float, safe_int, log_info, log_error, log_success, SYMBOL
)

# Timeframe configurations - same as live exporter
TIMEFRAME_LIMITS = {
    "M1": 120,   # ~2 hours
    "M5": 288,   # 1 day  
    "M15": 192,  # 2 days
    "H1": 480,   # 20 days
    "H4": 300,   # ~2 months
    "D1": 250    # ~1 year
}


def get_historical_m1_timestamps(symbol: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[datetime]:
    """
    Get all M1 timestamps for historical processing.
    
    Args:
        symbol: Trading symbol
        start_date: Start date for historical data (optional)
        end_date: End date for historical data (optional)
        
    Returns:
        List of M1 timestamps sorted ascending
    """
    timestamps = []
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            # Build the query with optional date filters
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
            
            timestamps = [row[0] for row in rows]
            
        log_info(f"Found {len(timestamps)} M1 timestamps for historical processing")
        
    except Exception as e:
        log_error(f"Failed to get historical M1 timestamps: {e}")
        
    return timestamps


def fetch_historical_ohlc_for_timeframe(symbol: str, timeframe: str, reference_time: datetime, limit: int) -> List[Dict[str, Any]]:
    """
    Fetch OHLC data for a timeframe at a specific point in time.
    Only includes candles that would have been available at reference_time.
    """
    candles = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get candles available at or before reference_time
            cur.execute("""
                SELECT 
                    open_time, open_price, high_price, low_price, close_price, volume,
                    adx, atr, bb_middle, bb_upper, bb_lower, cci, ema,
                    macd, macd_signal, macd_hist, obv, rsi, sma,
                    stochastic_k, stochastic_d, willr
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = %s AND open_time <= %s
                ORDER BY open_time DESC
                LIMIT %s
            """, (symbol, timeframe, reference_time, limit))
            
            rows = cur.fetchall()
            
            # Convert to list of dicts, sorted oldest first
            for row in reversed(rows):
                candle = {
                    "open_time": format_timestamp_utc(row["open_time"]),
                    "open": safe_float(row["open_price"]),
                    "high": safe_float(row["high_price"]),
                    "low": safe_float(row["low_price"]),
                    "close": safe_float(row["close_price"]),
                    "volume": safe_int(row["volume"]),
                    "adx": safe_float(row["adx"]),
                    "atr": safe_float(row["atr"]),
                    "bb_middle": safe_float(row["bb_middle"]),
                    "bb_upper": safe_float(row["bb_upper"]),
                    "bb_lower": safe_float(row["bb_lower"]),
                    "cci": safe_float(row["cci"]),
                    "ema": safe_float(row["ema"]),
                    "macd": safe_float(row["macd"]),
                    "macd_signal": safe_float(row["macd_signal"]),
                    "macd_hist": safe_float(row["macd_hist"]),
                    "obv": safe_float(row["obv"]),
                    "rsi": safe_float(row["rsi"]),
                    "sma": safe_float(row["sma"]),
                    "stoch_k": safe_float(row["stochastic_k"]),
                    "stoch_d": safe_float(row["stochastic_d"]),
                    "willr": safe_float(row["willr"]),
                }
                candles.append(candle)
                
    except Exception as e:
        log_error(f"Failed to fetch historical {timeframe} data: {e}")
        
    return candles


def build_historical_ohlc_snapshot(symbol: str, m1_timestamp: datetime) -> Dict[str, Any]:
    """
    Build OHLC snapshot for a specific M1 timestamp.
    
    Args:
        symbol: Trading symbol
        m1_timestamp: The M1 timestamp to build snapshot for
        
    Returns:
        OHLC JSON data structure
    """
    # Fetch data for all timeframes at this point in time
    timeframes_data = {}
    ohlc_last_time = {}
    
    for timeframe, limit in TIMEFRAME_LIMITS.items():
        candles = fetch_historical_ohlc_for_timeframe(symbol, timeframe, m1_timestamp, limit)
        timeframes_data[timeframe] = candles
        
        # Set last time for this timeframe
        if candles:
            ohlc_last_time[timeframe] = candles[-1]["open_time"]
        else:
            ohlc_last_time[timeframe] = None
    
    # Build the JSON structure
    ohlc_json = {
        "symbol": symbol,
        "timestamp": format_timestamp_utc(m1_timestamp),
        "ohlc": timeframes_data,
        "ohlc_last_time": ohlc_last_time,
        "last_update": format_timestamp_utc(m1_timestamp)
    }
    
    return ohlc_json


def check_existing_snapshot(symbol: str, snapshot_time: datetime) -> bool:
    """Check if a snapshot already exists for this symbol and time."""
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                SELECT 1 FROM trading_snapshots
                WHERE symbol = %s AND snapshot_time = %s AND ohlc_all_json IS NOT NULL
                LIMIT 1
            """, (symbol, snapshot_time))
            
            return cur.fetchone() is not None
            
    except Exception as e:
        log_error(f"Failed to check existing snapshot: {e}")
        return False


def export_ohlc_historical_batch(symbol: str, m1_timestamps: List[datetime], skip_existing: bool = True) -> int:
    """
    Export historical OHLC data for a batch of M1 timestamps.
    
    Args:
        symbol: Trading symbol
        m1_timestamps: List of M1 timestamps to process
        skip_existing: Skip timestamps that already have snapshots
        
    Returns:
        Number of successfully processed snapshots
    """
    successful_count = 0
    
    for i, m1_timestamp in enumerate(m1_timestamps):
        try:
            # Skip if snapshot already exists
            if skip_existing and check_existing_snapshot(symbol, m1_timestamp):
                if i % 100 == 0:  # Log every 100 skipped
                    log_info(f"Skipping existing snapshot {i+1}/{len(m1_timestamps)}: {m1_timestamp}")
                continue
            
            # Build historical snapshot
            ohlc_json = build_historical_ohlc_snapshot(symbol, m1_timestamp)
            
            # Insert into database
            success = insert_snapshot(
                symbol=symbol,
                snapshot_time=m1_timestamp,
                json_column_name="ohlc_all_json",
                json_data=ohlc_json
            )
            
            if success:
                successful_count += 1
                
            # Log progress every 100 snapshots
            if (i + 1) % 100 == 0:
                log_info(f"Processed {i + 1}/{len(m1_timestamps)} snapshots ({successful_count} successful)")
                
        except Exception as e:
            log_error(f"Failed to process snapshot for {m1_timestamp}: {e}")
    
    return successful_count


def export_ohlc_historical(
    symbol: str = None, 
    start_date: Optional[datetime] = None, 
    end_date: Optional[datetime] = None,
    batch_size: int = 1000,
    skip_existing: bool = True
) -> bool:
    """
    Export historical OHLC data for all M1 timestamps.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        start_date: Start date for historical data
        end_date: End date for historical data
        batch_size: Number of timestamps to process per batch
        skip_existing: Skip timestamps that already have snapshots
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
    
    log_info(f"Starting OHLC historical export for {symbol}")
    if start_date:
        log_info(f"Start date: {start_date}")
    if end_date:
        log_info(f"End date: {end_date}")
    
    try:
        # Get all M1 timestamps
        m1_timestamps = get_historical_m1_timestamps(symbol, start_date, end_date)
        
        if not m1_timestamps:
            log_error("No M1 timestamps found for historical processing")
            return False
        
        log_info(f"Processing {len(m1_timestamps)} M1 timestamps in batches of {batch_size}")
        
        total_successful = 0
        
        # Process in batches
        for i in range(0, len(m1_timestamps), batch_size):
            batch = m1_timestamps[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(m1_timestamps) + batch_size - 1) // batch_size
            
            log_info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} timestamps)")
            
            batch_successful = export_ohlc_historical_batch(symbol, batch, skip_existing)
            total_successful += batch_successful
            
            log_success(f"Batch {batch_num} completed: {batch_successful}/{len(batch)} successful")
            
            # Small delay between batches to avoid overwhelming the database
            if i + batch_size < len(m1_timestamps):
                time.sleep(1)
        
        log_success(f"OHLC historical export completed: {total_successful}/{len(m1_timestamps)} snapshots processed")
        return True
        
    except Exception as e:
        log_error(f"OHLC historical export failed: {e}")
        return False


def main():
    """Main entry point with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="OHLC Historical Data Exporter")
    
    parser.add_argument('--symbol', type=str, default=SYMBOL, help=f'Trading symbol (default: {SYMBOL})')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size (default: 1000)')
    parser.add_argument('--force', action='store_true', help='Overwrite existing snapshots')
    parser.add_argument('--last-week', action='store_true', help='Process last week only')
    parser.add_argument('--last-month', action='store_true', help='Process last month only')
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = None
    end_date = None
    
    if args.last_week:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(weeks=1)
    elif args.last_month:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
    else:
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    # Run export
    success = export_ohlc_historical(
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date,
        batch_size=args.batch_size,
        skip_existing=not args.force
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
