#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Max Gain/Loss Calculator - Feature 7
Calculates maximum gain and loss percentages for OHLC snapshots.

This script:
1. Finds snapshots that need max gain/loss calculations
2. For each snapshot, calculates gain/loss over the next 60 minutes
3. Updates trading_snapshots with calculation results
4. Handles both historical and live modes
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

from common import (
    get_cursor, format_timestamp_utc, safe_float,
    log_info, log_error, log_success, SYMBOL
)


def get_snapshots_needing_calculation(symbol: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Get snapshots that need max gain/loss calculations.
    
    Args:
        symbol: Trading symbol
        limit: Maximum number of snapshots to process
        
    Returns:
        List of snapshot records
    """
    snapshots = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT symbol, snapshot_time, ohlc_all_json
                FROM trading_snapshots
                WHERE symbol = %s 
                AND ohlc_all_json IS NOT NULL
                AND max_gain_pct_1h IS NULL
                ORDER BY snapshot_time ASC
                LIMIT %s
            """, (symbol, limit))
            
            rows = cur.fetchall()
            snapshots = [dict(row) for row in rows]
            
        log_info(f"Found {len(snapshots)} snapshots needing calculation")
        
    except Exception as e:
        log_error(f"Failed to get snapshots needing calculation: {e}")
        
    return snapshots


def get_m1_candles_for_calculation(symbol: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """
    Get M1 candles for gain/loss calculation.
    
    Args:
        symbol: Trading symbol
        start_time: Start time (snapshot time)
        end_time: End time (snapshot time + 60 minutes)
        
    Returns:
        List of M1 candles in the time range
    """
    candles = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT open_time, open_price, high_price, low_price, close_price
                FROM ohlc_data
                WHERE symbol = %s 
                AND timeframe = 'M1'
                AND open_time > %s 
                AND open_time <= %s
                ORDER BY open_time ASC
            """, (symbol, start_time, end_time))
            
            rows = cur.fetchall()
            
            for row in rows:
                candle = {
                    "open_time": row["open_time"],
                    "open": safe_float(row["open_price"]),
                    "high": safe_float(row["high_price"]),
                    "low": safe_float(row["low_price"]),
                    "close": safe_float(row["close_price"])
                }
                candles.append(candle)
                
    except Exception as e:
        log_error(f"Failed to get M1 candles for calculation: {e}")
        
    return candles


def get_current_close_price(symbol: str, snapshot_time: datetime) -> Optional[float]:
    """
    Get the close price of the M1 candle at snapshot_time.
    
    Args:
        symbol: Trading symbol
        snapshot_time: Exact timestamp of the snapshot
        
    Returns:
        Close price at snapshot time, or None if not found
    """
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                SELECT close_price
                FROM ohlc_data
                WHERE symbol = %s 
                AND timeframe = 'M1'
                AND open_time = %s
                LIMIT 1
            """, (symbol, snapshot_time))
            
            row = cur.fetchone()
            return safe_float(row[0]) if row else None
            
    except Exception as e:
        log_error(f"Failed to get current close price: {e}")
        return None


def calculate_gain_loss_percentages(current_close: float, candles: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Calculate max gain and loss percentages.
    
    Args:
        current_close: Close price at snapshot time
        candles: List of M1 candles for the next hour
        
    Returns:
        Tuple of (max_gain_pct, max_loss_pct)
    """
    if not candles or current_close is None or current_close <= 0:
        return 0.0, 0.0
    
    # Get all high and low prices
    highs = [candle["high"] for candle in candles if candle["high"] is not None]
    lows = [candle["low"] for candle in candles if candle["low"] is not None]
    
    if not highs or not lows:
        return 0.0, 0.0
    
    # Calculate max gain and loss
    max_high = max(highs)
    min_low = min(lows)
    
    # Calculate percentages
    max_gain_pct = (max_high - current_close) / current_close * 100
    max_loss_pct = (min_low - current_close) / current_close * 100
    
    return round(max_gain_pct, 4), round(max_loss_pct, 4)


def update_snapshot_calculations(
    symbol: str, 
    snapshot_time: datetime, 
    max_gain_pct: float, 
    max_loss_pct: float,
    calculation_range_minutes: int,
    prediction_mode: bool
) -> bool:
    """
    Update snapshot with calculation results.
    
    Args:
        symbol: Trading symbol
        snapshot_time: Snapshot timestamp
        max_gain_pct: Maximum gain percentage
        max_loss_pct: Maximum loss percentage
        calculation_range_minutes: Number of minutes used for calculation
        prediction_mode: Whether this was calculated in prediction mode
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                UPDATE trading_snapshots
                SET 
                    max_gain_pct_1h = %s,
                    max_loss_pct_1h = %s,
                    calculation_range_minutes = %s,
                    prediction_mode = %s
                WHERE symbol = %s AND snapshot_time = %s
            """, (max_gain_pct, max_loss_pct, calculation_range_minutes, prediction_mode, symbol, snapshot_time))
            
            return True
            
    except Exception as e:
        log_error(f"Failed to update snapshot calculations: {e}")
        return False


def calculate_for_snapshot(snapshot: Dict[str, Any], mode: str = "historical") -> bool:
    """
    Calculate max gain/loss for a single snapshot.
    
    Args:
        snapshot: Snapshot record from database
        mode: "historical" or "live"
        
    Returns:
        bool: True if successful, False otherwise
    """
    symbol = snapshot["symbol"]
    snapshot_time = snapshot["snapshot_time"]
    
    try:
        # Get current close price at snapshot time
        current_close = get_current_close_price(symbol, snapshot_time)
        if current_close is None:
            log_error(f"No close price found for {symbol} at {snapshot_time}")
            return False
        
        # Calculate end time (snapshot + 60 minutes)
        end_time = snapshot_time + timedelta(minutes=60)
        
        # Get M1 candles for calculation
        candles = get_m1_candles_for_calculation(symbol, snapshot_time, end_time)
        
        calculation_range_minutes = len(candles)
        
        # Determine if we have enough data
        if calculation_range_minutes < 60:
            if mode == "historical":
                # Historical mode: if less than 60 minutes, set to NULL
                log_info(f"Insufficient data for {snapshot_time}: {calculation_range_minutes} minutes")
                return update_snapshot_calculations(
                    symbol, snapshot_time, None, None, calculation_range_minutes, False
                )
            else:
                # Live mode: set prediction_mode = True
                prediction_mode = True
        else:
            prediction_mode = False
        
        # Calculate gain/loss percentages
        max_gain_pct, max_loss_pct = calculate_gain_loss_percentages(current_close, candles)
        
        # Update database
        success = update_snapshot_calculations(
            symbol, snapshot_time, max_gain_pct, max_loss_pct, 
            calculation_range_minutes, prediction_mode
        )
        
        if success:
            log_info(f"Calculated for {snapshot_time}: gain={max_gain_pct}%, loss={max_loss_pct}%, range={calculation_range_minutes}min")
        
        return success
        
    except Exception as e:
        log_error(f"Failed to calculate for snapshot {snapshot_time}: {e}")
        return False


def calculate_historical_batch(symbol: str, batch_size: int = 100) -> int:
    """
    Calculate max gain/loss for a batch of historical snapshots.
    
    Args:
        symbol: Trading symbol
        batch_size: Number of snapshots to process per batch
        
    Returns:
        Number of successfully processed snapshots
    """
    snapshots = get_snapshots_needing_calculation(symbol, batch_size)
    
    if not snapshots:
        log_info("No snapshots found needing calculation")
        return 0
    
    successful_count = 0
    
    for i, snapshot in enumerate(snapshots):
        try:
            success = calculate_for_snapshot(snapshot, mode="historical")
            if success:
                successful_count += 1
                
            # Log progress every 10 snapshots
            if (i + 1) % 10 == 0:
                log_info(f"Processed {i + 1}/{len(snapshots)} snapshots ({successful_count} successful)")
                
        except Exception as e:
            log_error(f"Failed to process snapshot {i+1}: {e}")
    
    return successful_count


def calculate_live_pending(symbol: str) -> int:
    """
    Calculate max gain/loss for live snapshots that are exactly 60 minutes old.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Number of successfully processed snapshots
    """
    now = datetime.now(timezone.utc)
    target_time = now - timedelta(minutes=60)
    
    # Round to nearest minute
    target_time = target_time.replace(second=0, microsecond=0)
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT symbol, snapshot_time, ohlc_all_json
                FROM trading_snapshots
                WHERE symbol = %s 
                AND snapshot_time = %s
                AND ohlc_all_json IS NOT NULL
                AND max_gain_pct_1h IS NULL
                LIMIT 5
            """, (symbol, target_time))
            
            snapshots = [dict(row) for row in cur.fetchall()]
    
        if not snapshots:
            log_info(f"No live snapshots found at {target_time}")
            return 0
        
        successful_count = 0
        
        for snapshot in snapshots:
            try:
                success = calculate_for_snapshot(snapshot, mode="live")
                if success:
                    successful_count += 1
            except Exception as e:
                log_error(f"Failed to process live snapshot: {e}")
        
        return successful_count
        
    except Exception as e:
        log_error(f"Failed to calculate live pending: {e}")
        return 0


def run_historical_backfill(symbol: str = None, batch_size: int = 100) -> bool:
    """
    Run historical backfill for max gain/loss calculations.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        batch_size: Number of snapshots to process per batch
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
    
    log_info(f"Starting historical max gain/loss backfill for {symbol}")
    
    total_processed = 0
    
    try:
        while True:
            # Process a batch
            batch_successful = calculate_historical_batch(symbol, batch_size)
            
            if batch_successful == 0:
                # No more snapshots to process
                break
            
            total_processed += batch_successful
            log_success(f"Batch completed: {batch_successful} snapshots processed")
            
            # Small delay between batches
            time.sleep(2)
        
        log_success(f"Historical backfill completed: {total_processed} total snapshots processed")
        return True
        
    except Exception as e:
        log_error(f"Historical backfill failed: {e}")
        return False


def run_live_calculator(symbol: str = None, interval_seconds: int = 60) -> None:
    """
    Run live max gain/loss calculator continuously.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        interval_seconds: Seconds between checks (default: 60 for 1 minute)
    """
    if symbol is None:
        symbol = SYMBOL
    
    log_info(f"Starting live max gain/loss calculator for {symbol}")
    log_info("Press Ctrl+C to stop")
    
    while True:
        try:
            processed = calculate_live_pending(symbol)
            if processed > 0:
                log_success(f"Processed {processed} live calculations")
            
        except KeyboardInterrupt:
            log_info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            log_error(f"Unexpected error in live calculator: {e}")
        
        time.sleep(interval_seconds)


def main():
    """Main entry point with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Max Gain/Loss Calculator")
    
    parser.add_argument('--symbol', type=str, default=SYMBOL, help=f'Trading symbol (default: {SYMBOL})')
    parser.add_argument('--mode', choices=['historical', 'live'], default='historical', 
                       help='Calculation mode (default: historical)')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for historical mode (default: 100)')
    parser.add_argument('--interval', type=int, default=60, help='Interval for live mode in seconds (default: 60)')
    
    args = parser.parse_args()
    
    if args.mode == 'historical':
        success = run_historical_backfill(args.symbol, args.batch_size)
        exit(0 if success else 1)
    else:
        run_live_calculator(args.symbol, args.interval)


if __name__ == "__main__":
    main()
