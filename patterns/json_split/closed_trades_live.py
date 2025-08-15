#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Closed Trades Live             for row in rows:
                trade = {
                    "trade_id": row["id"],
                    "symbol": row["symbol"],
                    "type": row["type"],
                    "volume": safe_float(row["volume"]),
                    "open_price": safe_float(row["entry_price"]),
                    "close_price": safe_float(row["exit_price"]),
                    "stop_loss": None,  # Not available in closed_trades table
                    "take_profit": None,  # Not available in closed_trades table
                    "profit": safe_float(row["profit"]),
                    "commission": 0.0,  # Not available in closed_trades table
                    "swap": 0.0,  # Not available in closed_trades table
                    "open_time": format_timestamp_utc(row["time"]),
                    "close_time": format_timestamp_utc(row["time"]),
                    "comment": row["comment"] or "",
                    "magic": 0  # Not available in closed_trades table
                }ure 4
Exports recently closed trades to the database.

This script runs every minute and:
1. Fetches trades closed since the last snapshot
2. Calculates duration in minutes
3. Builds closed trades JSON structure
4. Stores it in trading_snapshots.closed_trades_json column
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from common import (
    get_cursor, insert_snapshot, get_latest_m1_time, get_latest_account_id,
    format_timestamp_utc, safe_float, safe_int,
    log_info, log_error, log_success, SYMBOL
)


def calculate_duration_minutes(open_time: datetime, close_time: datetime) -> int:
    """Calculate duration between open and close time in minutes."""
    try:
        # Ensure both times have timezone info
        if open_time.tzinfo is None:
            open_time = open_time.replace(tzinfo=timezone.utc)
        if close_time.tzinfo is None:
            close_time = close_time.replace(tzinfo=timezone.utc)
            
        duration = close_time - open_time
        return int(duration.total_seconds() / 60)
    except Exception as e:
        log_error(f"Failed to calculate duration: {e}")
        return 0


def fetch_recent_closed_trades(symbol: str, since_time: datetime) -> List[Dict[str, Any]]:
    """
    Fetch trades closed since the given time.
    Based on your existing database structure.
    """
    trades = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Note: Using your existing closed_trades table structure
            # You may need to adjust column names based on actual table structure
            cur.execute("""
                SELECT 
                    id, symbol, type, volume, entry_price, exit_price,
                    profit, comment, time, account_id, drawdown
                FROM closed_trades
                WHERE symbol = %s 
                AND time > %s
                ORDER BY time DESC
                LIMIT 50
            """, (symbol, since_time))
            
            rows = cur.fetchall()
            
            for row in rows:
                # For closed trades, we don't have separate open/close times
                # Use the 'time' field as close time and estimate open time
                close_time = row["time"]
                # For duration calculation, we'll use a default or skip if not available
                
                trade = {
                    "symbol": row["symbol"],
                    "magic": safe_int(row.get("account_id", 0)),  # Using account_id as magic equivalent
                    "order_type": row.get("type", "unknown"),
                    "lot_size": safe_float(row["volume"]),
                    "open_price": safe_float(row["entry_price"]),
                    "close_price": safe_float(row["exit_price"]),
                    "sl": None,  # Usually not stored in closed_trades
                    "tp": None,  # Usually not stored in closed_trades  
                    "profit": safe_float(row["profit"]),
                    "open_time": None,  # Not available in closed_trades table
                    "close_time": format_timestamp_utc(close_time),
                    "duration_minutes": None  # Cannot calculate without open_time
                }
                trades.append(trade)
                
        log_info(f"Fetched {len(trades)} recently closed trades")
                
    except Exception as e:
        log_error(f"Failed to fetch closed trades: {e}")
        
    return trades


def get_last_snapshot_time(symbol: str) -> Optional[datetime]:
    """Get the timestamp of the last snapshot for this symbol."""
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                SELECT snapshot_time
                FROM trading_snapshots
                WHERE symbol = %s AND closed_trades_json IS NOT NULL
                ORDER BY snapshot_time DESC
                LIMIT 1
            """, (symbol,))
            
            row = cur.fetchone()
            return row[0] if row else None
            
    except Exception as e:
        log_error(f"Failed to get last snapshot time: {e}")
        return None


def export_closed_trades_live(symbol: str = None) -> bool:
    """
    Export recently closed trades to database.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
        
    log_info(f"Starting closed trades live export for {symbol}")
    
    try:
        # Get the latest M1 candle time for snapshot_time
        latest_m1_time = get_latest_m1_time(symbol)
        if not latest_m1_time:
            log_error("No M1 data found")
            return False
        
        # Get the last snapshot time to determine "since when" to fetch closed trades
        last_snapshot_time = get_last_snapshot_time(symbol)
        
        # If no previous snapshot, fetch trades from last hour
        if last_snapshot_time is None:
            since_time = latest_m1_time - timedelta(hours=1)
            log_info("No previous snapshot found, fetching trades from last hour")
        else:
            since_time = last_snapshot_time
            log_info(f"Fetching trades closed since last snapshot: {since_time}")
        
        # Fetch recently closed trades
        trades_data = fetch_recent_closed_trades(symbol, since_time)
        
        # The JSON structure is an array of trades (even if empty)
        closed_trades_json = trades_data
        
        # Insert into database
        success = insert_snapshot(
            symbol=symbol,
            snapshot_time=latest_m1_time,
            json_column_name="closed_trades_json",
            json_data=closed_trades_json
        )
        
        if success:
            log_success(f"Closed trades live export completed for {symbol}")
            log_info(f"Exported {len(trades_data)} recently closed trades")
            return True
        else:
            log_error(f"Failed to insert closed trades data for {symbol}")
            return False
            
    except Exception as e:
        log_error(f"Closed trades live export failed: {e}")
        return False


def run_continuous(interval_seconds: int = 60):
    """
    Run the closed trades exporter continuously.
    
    Args:
        interval_seconds: Seconds between exports (default: 60 for 1 minute)
    """
    log_info(f"Starting continuous closed trades live export (interval: {interval_seconds}s)")
    
    while True:
        try:
            export_closed_trades_live()
        except KeyboardInterrupt:
            log_info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            log_error(f"Unexpected error in main loop: {e}")
        
        log_info(f"Waiting {interval_seconds} seconds for next export...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    # For testing, run once
    if len(__import__('sys').argv) > 1 and __import__('sys').argv[1] == "--continuous":
        run_continuous()
    else:
        log_info("Running single closed trades export (use --continuous for continuous mode)")
        success = export_closed_trades_live()
        exit(0 if success else 1)
