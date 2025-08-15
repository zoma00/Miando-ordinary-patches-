#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Market State Historical Exporter
Backfills market state data for historical snapshots.

This script:
1. Fetches market state data at historical points (spread, volume, volatility)
2. Formats as JSON and saves to market_state_json column
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


def get_snapshots_needing_market_state(symbol: str, start_date: datetime = None, 
                                     end_date: datetime = None, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get snapshots that need market state data.
    
    Args:
        symbol: Trading symbol
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of snapshots to return
        
    Returns:
        List of snapshot records
    """
    conditions = ["symbol = %s", "market_state_json IS NULL"]
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
            
        log_info(f"Found {len(snapshots)} snapshots needing market state data")
        
    except Exception as e:
        log_error(f"Failed to get snapshots needing market state: {e}")
        
    return snapshots


def calculate_market_metrics(symbol: str, target_time: datetime) -> Dict[str, Any]:
    """
    Calculate market state metrics at a specific time.
    
    Args:
        symbol: Trading symbol
        target_time: Target timestamp
        
    Returns:
        Dictionary containing market state metrics
    """
    metrics = {
        "timestamp": format_timestamp_utc(target_time),
        "symbol": symbol,
        "current_price": None,
        "spread": None,
        "volume_24h": None,
        "volatility": None,
        "market_session": None
    }
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get current M1 candle at target time
            cur.execute("""
                SELECT open_price, high_price, low_price, close_price, volume
                FROM ohlc_data
                WHERE symbol = %s 
                AND timeframe = 'M1'
                AND open_time = %s
                LIMIT 1
            """, (symbol, target_time))
            
            current_candle = cur.fetchone()
            
            if current_candle:
                metrics["current_price"] = safe_float(current_candle["close_price"])
                
                # Calculate spread (high - low of current candle)
                high = safe_float(current_candle["high_price"])
                low = safe_float(current_candle["low_price"])
                if high and low:
                    metrics["spread"] = round(high - low, 5)
            
            # Calculate 24-hour volume
            volume_start = target_time - timedelta(hours=24)
            cur.execute("""
                SELECT SUM(volume) as total_volume
                FROM ohlc_data
                WHERE symbol = %s 
                AND timeframe = 'M1'
                AND open_time > %s
                AND open_time <= %s
            """, (symbol, volume_start, target_time))
            
            volume_row = cur.fetchone()
            if volume_row and volume_row["total_volume"]:
                metrics["volume_24h"] = safe_float(volume_row["total_volume"])
            
            # Calculate volatility (standard deviation of M5 closes over last 4 hours)
            volatility_start = target_time - timedelta(hours=4)
            cur.execute("""
                SELECT close_price
                FROM ohlc_data
                WHERE symbol = %s 
                AND timeframe = 'M5'
                AND open_time > %s
                AND open_time <= %s
                ORDER BY open_time ASC
            """, (symbol, volatility_start, target_time))
            
            price_rows = cur.fetchall()
            if len(price_rows) > 1:
                prices = [safe_float(row["close_price"]) for row in price_rows if row["close_price"]]
                if len(prices) > 1:
                    # Calculate standard deviation
                    mean_price = sum(prices) / len(prices)
                    variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
                    volatility = variance ** 0.5
                    metrics["volatility"] = round(volatility, 5)
            
            # Determine market session based on time
            hour = target_time.hour
            if 0 <= hour < 6:
                metrics["market_session"] = "Asian"
            elif 6 <= hour < 14:
                metrics["market_session"] = "European"
            elif 14 <= hour < 22:
                metrics["market_session"] = "American"
            else:
                metrics["market_session"] = "Asian"
                
    except Exception as e:
        log_error(f"Failed to calculate market metrics at {target_time}: {e}")
        
    return metrics


def export_market_state_for_snapshot(symbol: str, snapshot_time: datetime) -> bool:
    """
    Export market state data for a specific snapshot.
    
    Args:
        symbol: Trading symbol
        snapshot_time: Snapshot timestamp
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Calculate market state metrics
        market_state = calculate_market_metrics(symbol, snapshot_time)
        
        # Convert to JSON
        market_state_json = json.dumps(market_state, ensure_ascii=False, separators=(',', ':'))
        
        # Update snapshot
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                UPDATE trading_snapshots
                SET market_state_json = %s
                WHERE symbol = %s AND snapshot_time = %s
            """, (market_state_json, symbol, snapshot_time))
        
        log_info(f"Exported market state for {symbol} at {snapshot_time}")
        return True
        
    except Exception as e:
        log_error(f"Failed to export market state for {symbol} at {snapshot_time}: {e}")
        return False


def process_historical_batch(snapshots: List[Dict[str, Any]]) -> int:
    """
    Process a batch of snapshots for market state export.
    
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
            success = export_market_state_for_snapshot(symbol, snapshot_time)
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
    Run historical market state export.
    
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
        
    log_info(f"Starting historical market state export for {symbol}")
    
    if start_date:
        log_info(f"Start date: {start_date}")
    if end_date:
        log_info(f"End date: {end_date}")
    
    total_processed = 0
    
    try:
        while True:
            # Get batch of snapshots needing market state data
            snapshots = get_snapshots_needing_market_state(symbol, start_date, end_date, batch_size)
            
            if not snapshots:
                log_info("No more snapshots found needing market state data")
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
        
        log_success(f"Historical market state export completed: {total_processed} total snapshots processed")
        return True
        
    except Exception as e:
        log_error(f"Historical market state export failed: {e}")
        return False


def main():
    """Main entry point with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Market State Historical Exporter")
    
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
