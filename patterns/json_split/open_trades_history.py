#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Open Trades Historical Exporter
Backfills open trades data for historical snapshots.

This script:
1. Fetches open trades data at historical points
2. Formats as JSON and saves to open_trades_json column
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


def get_snapshots_needing_open_trades(symbol: str, start_date: datetime = None, 
                                    end_date: datetime = None, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get snapshots that need open trades data.
    
    Args:
        symbol: Trading symbol
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of snapshots to return
        
    Returns:
        List of snapshot records
    """
    conditions = ["symbol = %s", "open_trades_json IS NULL"]
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
            
        log_info(f"Found {len(snapshots)} snapshots needing open trades data")
        
    except Exception as e:
        log_error(f"Failed to get snapshots needing open trades: {e}")
        
    return snapshots


def fetch_open_trades_at_time(symbol: str, target_time: datetime) -> List[Dict[str, Any]]:
    """
    Fetch open trades data at a specific time.
    
    Args:
        symbol: Trading symbol
        target_time: Target timestamp
        
    Returns:
        List of open trades as dictionaries
    """
    open_trades = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get all trades that were open at the target time
            cur.execute("""
                SELECT 
                    trade_id, symbol, order_type, lot_size, open_price, 
                    sl, tp, open_time, status, comment, magic_number
                FROM open_trades
                WHERE symbol = %s 
                AND open_time <= %s
                AND (close_time IS NULL OR close_time > %s)
                ORDER BY open_time ASC
            """, (symbol, target_time, target_time))
            
            rows = cur.fetchall()
            
            for row in rows:
                trade = {
                    "trade_id": row["trade_id"],
                    "symbol": row["symbol"],
                    "type": row["order_type"],
                    "volume": safe_float(row["lot_size"]),
                    "open_price": safe_float(row["open_price"]),
                    "stop_loss": safe_float(row["sl"]),
                    "take_profit": safe_float(row["tp"]),
                    "profit": 0.0,  # Open trades don't have profit yet
                    "commission": 0.0,  # Not available in open_trades table
                    "swap": 0.0,  # Not available in open_trades table
                    "open_time": format_timestamp_utc(row["open_time"]),
                    "comment": row["comment"] or "",
                    "magic": row["magic_number"] or 0
                }
                open_trades.append(trade)
                
    except Exception as e:
        log_error(f"Failed to fetch open trades at {target_time}: {e}")
        
    return open_trades


def export_open_trades_for_snapshot(symbol: str, snapshot_time: datetime) -> bool:
    """
    Export open trades data for a specific snapshot.
    
    Args:
        symbol: Trading symbol
        snapshot_time: Snapshot timestamp
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Fetch open trades data
        open_trades = fetch_open_trades_at_time(symbol, snapshot_time)
        
        # Convert to JSON
        open_trades_json = json.dumps(open_trades, ensure_ascii=False, separators=(',', ':'))
        
        # Update snapshot
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                UPDATE trading_snapshots
                SET open_trades_json = %s
                WHERE symbol = %s AND snapshot_time = %s
            """, (open_trades_json, symbol, snapshot_time))
        
        log_info(f"Exported {len(open_trades)} open trades for {symbol} at {snapshot_time}")
        return True
        
    except Exception as e:
        log_error(f"Failed to export open trades for {symbol} at {snapshot_time}: {e}")
        return False


def process_historical_batch(snapshots: List[Dict[str, Any]]) -> int:
    """
    Process a batch of snapshots for open trades export.
    
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
            success = export_open_trades_for_snapshot(symbol, snapshot_time)
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
    Run historical open trades export.
    
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
        
    log_info(f"Starting historical open trades export for {symbol}")
    
    if start_date:
        log_info(f"Start date: {start_date}")
    if end_date:
        log_info(f"End date: {end_date}")
    
    total_processed = 0
    
    try:
        while True:
            # Get batch of snapshots needing open trades data
            snapshots = get_snapshots_needing_open_trades(symbol, start_date, end_date, batch_size)
            
            if not snapshots:
                log_info("No more snapshots found needing open trades data")
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
        
        log_success(f"Historical open trades export completed: {total_processed} total snapshots processed")
        return True
        
    except Exception as e:
        log_error(f"Historical open trades export failed: {e}")
        return False


def main():
    """Main entry point with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Open Trades Historical Exporter")
    
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
