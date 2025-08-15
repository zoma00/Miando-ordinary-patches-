#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Account State Historical Exporter
Backfills account state data for historical snapshots.

This script:
1. Fetches account state data at historical points
2. Formats as JSON and saves to account_state_json column
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


def get_snapshots_needing_account_state(symbol: str, start_date: datetime = None, 
                                      end_date: datetime = None, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get snapshots that need account state data.
    
    Args:
        symbol: Trading symbol
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of snapshots to return
        
    Returns:
        List of snapshot records
    """
    conditions = ["symbol = %s", "account_state_json IS NULL"]
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
            
        log_info(f"Found {len(snapshots)} snapshots needing account state data")
        
    except Exception as e:
        log_error(f"Failed to get snapshots needing account state: {e}")
        
    return snapshots


def fetch_account_state_at_time(symbol: str, target_time: datetime) -> Optional[Dict[str, Any]]:
    """
    Fetch account state data at a specific time.
    
    Args:
        symbol: Trading symbol
        target_time: Target timestamp
        
    Returns:
        Account state data as dictionary, or None if not found
    """
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get account balance, equity, and margin information
            # Find the closest account state before or at target_time
            cur.execute("""
                SELECT 
                    balance, equity, margin, free_margin, margin_level,
                    profit_loss, total_positions, risk_percent,
                    created_at
                FROM account_state
                WHERE symbol = %s 
                AND created_at <= %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (symbol, target_time))
            
            row = cur.fetchone()
            if not row:
                return None
            
            account_state = {
                "balance": safe_float(row["balance"]),
                "equity": safe_float(row["equity"]), 
                "margin": safe_float(row["margin"]),
                "free_margin": safe_float(row["free_margin"]),
                "margin_level": safe_float(row["margin_level"]),
                "profit_loss": safe_float(row["profit_loss"]),
                "total_positions": row["total_positions"] or 0,
                "risk_percent": safe_float(row["risk_percent"]),
                "timestamp": format_timestamp_utc(row["created_at"]),
                "symbol": symbol
            }
            
            return account_state
            
    except Exception as e:
        log_error(f"Failed to fetch account state at {target_time}: {e}")
        return None


def export_account_state_for_snapshot(symbol: str, snapshot_time: datetime) -> bool:
    """
    Export account state data for a specific snapshot.
    
    Args:
        symbol: Trading symbol
        snapshot_time: Snapshot timestamp
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Fetch account state data
        account_state = fetch_account_state_at_time(symbol, snapshot_time)
        
        if account_state is None:
            log_error(f"No account state data found for {symbol} at {snapshot_time}")
            return False
        
        # Convert to JSON
        account_state_json = json.dumps(account_state, ensure_ascii=False, separators=(',', ':'))
        
        # Update snapshot
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                UPDATE trading_snapshots
                SET account_state_json = %s
                WHERE symbol = %s AND snapshot_time = %s
            """, (account_state_json, symbol, snapshot_time))
        
        log_info(f"Exported account state for {symbol} at {snapshot_time}")
        return True
        
    except Exception as e:
        log_error(f"Failed to export account state for {symbol} at {snapshot_time}: {e}")
        return False


def process_historical_batch(snapshots: List[Dict[str, Any]]) -> int:
    """
    Process a batch of snapshots for account state export.
    
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
            success = export_account_state_for_snapshot(symbol, snapshot_time)
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
    Run historical account state export.
    
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
        
    log_info(f"Starting historical account state export for {symbol}")
    
    if start_date:
        log_info(f"Start date: {start_date}")
    if end_date:
        log_info(f"End date: {end_date}")
    
    total_processed = 0
    
    try:
        while True:
            # Get batch of snapshots needing account state data
            snapshots = get_snapshots_needing_account_state(symbol, start_date, end_date, batch_size)
            
            if not snapshots:
                log_info("No more snapshots found needing account state data")
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
        
        log_success(f"Historical account state export completed: {total_processed} total snapshots processed")
        return True
        
    except Exception as e:
        log_error(f"Historical account state export failed: {e}")
        return False


def main():
    """Main entry point with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Account State Historical Exporter")
    
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
