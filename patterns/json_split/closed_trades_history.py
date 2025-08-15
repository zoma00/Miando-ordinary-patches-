#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Closed Trades Historical Exporter
Backfills closed trades data for historical snapshots.

This script:
1. Fetches closed trades data at historical points (last 24 hours from snapshot)
2. Formats as JSON and saves to closed_trades_json column
3. Handles batch processing for efficient historical backfill
4. Provides date range filtering and existing data checks
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from common import (
    get_cursor, format_timestamp_utc, safe_float,
    log_info, log_error, log_success, SYMBOL
)


def get_snapshots_needing_closed_trades(symbol: str, start_date: datetime = None, 
                                      end_date: datetime = None, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get snapshots that need closed trades data.
    
    Args:
        symbol: Trading symbol
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of snapshots to return
        
    Returns:
        List of snapshot records
    """
    conditions = ["symbol = %s", "closed_trades_json IS NULL"]
    params = [symbol]
    
    if start_date:
        conditions.append("snapshot_time >= %s")
        params.append(start_date)
    
    if end_date:
        conditions.append("snapshot_time <= %s")
        params.append(end_date)
    
    snapshots = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            query = f"""
                SELECT symbol, snapshot_time
                FROM trading_snapshots
                WHERE {' AND '.join(conditions)}
                ORDER BY snapshot_time ASC
                LIMIT %s
            """
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            snapshots = [dict(row) for row in rows]
            
        log_info(f"Found {len(snapshots)} snapshots needing closed trades data")
        
    except Exception as e:
        log_error(f"Failed to get snapshots needing closed trades: {e}")
        
    return snapshots


def fetch_closed_trades_in_range(symbol: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """
    Fetch closed trades data within a time range.
    
    Args:
        symbol: Trading symbol
        start_time: Start time for the range (24 hours before snapshot)
        end_time: End time for the range (snapshot time)
        
    Returns:
        List of closed trades as dictionaries
    """
    closed_trades = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get all trades that were closed in the time range
            cur.execute("""
                SELECT 
                    id, symbol, type, volume, entry_price, exit_price,
                    profit, comment, time, account_id, drawdown
                FROM closed_trades
                WHERE symbol = %s 
                AND time > %s
                AND time <= %s
                ORDER BY time DESC
            """, (symbol, start_time, end_time))
            
            rows = cur.fetchall()
            
            for row in rows:
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
                }
                closed_trades.append(trade)
                
    except Exception as e:
        log_error(f"Failed to fetch closed trades in range {start_time} to {end_time}: {e}")
        
    return closed_trades


def export_closed_trades_for_snapshot(symbol: str, snapshot_time: datetime) -> bool:
    """
    Export closed trades data for a specific snapshot.
    
    Args:
        symbol: Trading symbol
        snapshot_time: Snapshot timestamp
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Calculate time range (24 hours before snapshot)
        start_time = snapshot_time - timedelta(hours=24)
        
        # Fetch closed trades data
        closed_trades = fetch_closed_trades_in_range(symbol, start_time, snapshot_time)
        
        # Convert to JSON
        closed_trades_json = json.dumps(closed_trades, ensure_ascii=False, separators=(',', ':'))
        
        # Update snapshot
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                UPDATE trading_snapshots
                SET closed_trades_json = %s
                WHERE symbol = %s AND snapshot_time = %s
            """, (closed_trades_json, symbol, snapshot_time))
        
        log_info(f"Exported {len(closed_trades)} closed trades for {symbol} at {snapshot_time}")
        return True
        
    except Exception as e:
        log_error(f"Failed to export closed trades for {symbol} at {snapshot_time}: {e}")
        return False


def process_historical_batch(snapshots: List[Dict[str, Any]]) -> int:
    """
    Process a batch of snapshots for closed trades export.
    
    Args:
        snapshots: List of snapshot records
        
    Returns:
        Number of successfully processed snapshots
    """
    successful_count = 0
    
    for i, snapshot in enumerate(snapshots):
        symbol = snapshot["symbol"]
        snapshot_time = snapshot["snapshot_time"]
        
        try:
            success = export_closed_trades_for_snapshot(symbol, snapshot_time)
            if success:
                successful_count += 1
                
            # Log progress every 25 snapshots
            if (i + 1) % 25 == 0:
                log_info(f"Processed {i + 1}/{len(snapshots)} snapshots ({successful_count} successful)")
                
        except Exception as e:
            log_error(f"Failed to process snapshot {i+1}: {e}")
    
    return successful_count


def run_historical_export(symbol: str = None, start_date: datetime = None, 
                         end_date: datetime = None, batch_size: int = 1000) -> bool:
    """
    Run historical closed trades export.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        start_date: Optional start date filter
        end_date: Optional end date filter  
        batch_size: Number of snapshots to process per batch
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
        
    log_info(f"Starting historical closed trades export for {symbol}")
    
    if start_date:
        log_info(f"Start date: {start_date}")
    if end_date:
        log_info(f"End date: {end_date}")
    
    total_processed = 0
    
    try:
        while True:
            # Get batch of snapshots needing closed trades data
            snapshots = get_snapshots_needing_closed_trades(symbol, start_date, end_date, batch_size)
            
            if not snapshots:
                log_info("No more snapshots found needing closed trades data")
                break
            
            # Process batch
            batch_successful = process_historical_batch(snapshots)
            total_processed += batch_successful
            
            log_success(f"Batch completed: {batch_successful}/{len(snapshots)} snapshots processed")
            
            # If we got fewer snapshots than batch_size, we're done
            if len(snapshots) < batch_size:
                break
            
            # Brief delay between batches
            time.sleep(1)
        
        log_success(f"Historical closed trades export completed: {total_processed} total snapshots processed")
        return True
        
    except Exception as e:
        log_error(f"Historical closed trades export failed: {e}")
        return False


def main():
    """Main entry point with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Closed Trades Historical Exporter")
    
    parser.add_argument('--symbol', type=str, default=SYMBOL, help=f'Trading symbol (default: {SYMBOL})')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size (default: 1000)')
    parser.add_argument('--last-week', action='store_true', 
                       help='Export only last week of data')
    parser.add_argument('--last-month', action='store_true', 
                       help='Export only last month of data')
    parser.add_argument('--start-date', type=str, 
                       help='Start date (YYYY-MM-DD format)')
    parser.add_argument('--end-date', type=str, 
                       help='End date (YYYY-MM-DD format)')
    
    args = parser.parse_args()
    
    start_date = None
    end_date = None
    
    # Handle date range options
    if args.last_week:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
    elif args.last_month:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
    else:
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    # Run export
    success = run_historical_export(args.symbol, start_date, end_date, args.batch_size)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
