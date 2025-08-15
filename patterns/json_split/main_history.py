#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Historical Data Backfill Coordinator
Orchestrates historical data backfill for all JSON split components.

This script:
1. Coordinates historical export for all data types
2. Manages backfill order and dependencies
3. Provides unified command-line interface
4. Handles error recovery and progress reporting
"""

import time
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from common import log_info, log_error, log_success, SYMBOL


def run_script(script_name: str, args: List[str] = None) -> bool:
    """
    Run a Python script with arguments.
    
    Args:
        script_name: Name of the script to run
        args: List of command line arguments
        
    Returns:
        bool: True if successful, False otherwise
    """
    if args is None:
        args = []
    
    cmd = [sys.executable, script_name] + args
    
    try:
        log_info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            log_success(f"Successfully completed {script_name}")
            return True
        else:
            log_error(f"Failed to run {script_name} (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        log_error(f"Error running {script_name}: {e}")
        return False


def backfill_ohlc_data(symbol: str, start_date: str = None, end_date: str = None, 
                      batch_size: int = 1000) -> bool:
    """
    Backfill OHLC data.
    
    Args:
        symbol: Trading symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        batch_size: Batch size for processing
        
    Returns:
        bool: True if successful
    """
    log_info("Starting OHLC data backfill...")
    
    args = ['--symbol', symbol, '--batch-size', str(batch_size)]
    
    if start_date:
        args.extend(['--start-date', start_date])
    if end_date:
        args.extend(['--end-date', end_date])
    
    return run_script('ohlc_all_history.py', args)


def backfill_account_state(symbol: str, start_date: str = None, end_date: str = None, 
                          batch_size: int = 1000) -> bool:
    """
    Backfill account state data.
    
    Args:
        symbol: Trading symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        batch_size: Batch size for processing
        
    Returns:
        bool: True if successful
    """
    log_info("Starting account state backfill...")
    
    args = ['--symbol', symbol, '--batch-size', str(batch_size)]
    
    if start_date:
        args.extend(['--start-date', start_date])
    if end_date:
        args.extend(['--end-date', end_date])
    
    return run_script('account_state_history.py', args)


def backfill_open_trades(symbol: str, start_date: str = None, end_date: str = None, 
                        batch_size: int = 1000) -> bool:
    """
    Backfill open trades data.
    
    Args:
        symbol: Trading symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        batch_size: Batch size for processing
        
    Returns:
        bool: True if successful
    """
    log_info("Starting open trades backfill...")
    
    args = ['--symbol', symbol, '--batch-size', str(batch_size)]
    
    if start_date:
        args.extend(['--start-date', start_date])
    if end_date:
        args.extend(['--end-date', end_date])
    
    return run_script('open_trades_history.py', args)


def backfill_closed_trades(symbol: str, start_date: str = None, end_date: str = None, 
                          batch_size: int = 1000) -> bool:
    """
    Backfill closed trades data.
    
    Args:
        symbol: Trading symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        batch_size: Batch size for processing
        
    Returns:
        bool: True if successful
    """
    log_info("Starting closed trades backfill...")
    
    args = ['--symbol', symbol, '--batch-size', str(batch_size)]
    
    if start_date:
        args.extend(['--start-date', start_date])
    if end_date:
        args.extend(['--end-date', end_date])
    
    return run_script('closed_trades_history.py', args)


def backfill_market_state(symbol: str, start_date: str = None, end_date: str = None, 
                         batch_size: int = 1000) -> bool:
    """
    Backfill market state data.
    
    Args:
        symbol: Trading symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        batch_size: Batch size for processing
        
    Returns:
        bool: True if successful
    """
    log_info("Starting market state backfill...")
    
    args = ['--symbol', symbol, '--batch-size', str(batch_size)]
    
    if start_date:
        args.extend(['--start-date', start_date])
    if end_date:
        args.extend(['--end-date', end_date])
    
    return run_script('market_state_history.py', args)


def backfill_max_gain_loss(symbol: str, batch_size: int = 100) -> bool:
    """
    Backfill max gain/loss calculations.
    
    Args:
        symbol: Trading symbol
        batch_size: Batch size for processing
        
    Returns:
        bool: True if successful
    """
    log_info("Starting max gain/loss calculations backfill...")
    
    args = ['--symbol', symbol, '--mode', 'historical', '--batch-size', str(batch_size)]
    
    return run_script('max_gain_loss_calc.py', args)


def run_complete_backfill(symbol: str = None, start_date: str = None, end_date: str = None, 
                         batch_size: int = 1000, skip_max_gain_loss: bool = False) -> bool:
    """
    Run complete historical backfill for all data types.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        batch_size: Batch size for processing
        skip_max_gain_loss: Skip max gain/loss calculations (computationally intensive)
        
    Returns:
        bool: True if all successful
    """
    if symbol is None:
        symbol = SYMBOL
    
    log_info(f"Starting complete historical backfill for {symbol}")
    log_info("=" * 60)
    
    if start_date:
        log_info(f"Date range: {start_date} to {end_date or 'present'}")
    
    # Define backfill steps in order
    steps = [
        ("OHLC Data", lambda: backfill_ohlc_data(symbol, start_date, end_date, batch_size)),
        ("Account State", lambda: backfill_account_state(symbol, start_date, end_date, batch_size)),
        ("Open Trades", lambda: backfill_open_trades(symbol, start_date, end_date, batch_size)),
        ("Closed Trades", lambda: backfill_closed_trades(symbol, start_date, end_date, batch_size)),
        ("Market State", lambda: backfill_market_state(symbol, start_date, end_date, batch_size)),
    ]
    
    # Add max gain/loss step if not skipped
    if not skip_max_gain_loss:
        steps.append(("Max Gain/Loss", lambda: backfill_max_gain_loss(symbol, min(batch_size, 100))))
    
    # Execute all steps
    successful_steps = 0
    
    for step_name, step_func in steps:
        log_info(f"\n--- Step {successful_steps + 1}/{len(steps)}: {step_name} ---")
        
        try:
            success = step_func()
            if success:
                successful_steps += 1
                log_success(f"✅ {step_name} completed successfully")
            else:
                log_error(f"❌ {step_name} failed")
        except Exception as e:
            log_error(f"❌ {step_name} failed with exception: {e}")
        
        # Brief pause between steps
        time.sleep(2)
    
    # Report final results
    log_info("=" * 60)
    log_info(f"Backfill Summary: {successful_steps}/{len(steps)} steps completed")
    
    if successful_steps == len(steps):
        log_success("🎉 Complete historical backfill successful!")
        return True
    else:
        log_error(f"⚠️ Backfill completed with {len(steps) - successful_steps} failures")
        return False


def run_selective_backfill(symbol: str = None, data_types: List[str] = None, 
                          start_date: str = None, end_date: str = None, 
                          batch_size: int = 1000) -> bool:
    """
    Run selective backfill for specific data types.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        data_types: List of data types to backfill
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        batch_size: Batch size for processing
        
    Returns:
        bool: True if all selected types successful
    """
    if symbol is None:
        symbol = SYMBOL
    
    if not data_types:
        log_error("No data types specified for selective backfill")
        return False
    
    log_info(f"Starting selective backfill for {symbol}")
    log_info(f"Data types: {', '.join(data_types)}")
    
    # Define available backfill functions
    backfill_functions = {
        'ohlc': lambda: backfill_ohlc_data(symbol, start_date, end_date, batch_size),
        'account': lambda: backfill_account_state(symbol, start_date, end_date, batch_size),
        'open_trades': lambda: backfill_open_trades(symbol, start_date, end_date, batch_size),
        'closed_trades': lambda: backfill_closed_trades(symbol, start_date, end_date, batch_size),
        'market': lambda: backfill_market_state(symbol, start_date, end_date, batch_size),
        'max_gain_loss': lambda: backfill_max_gain_loss(symbol, min(batch_size, 100)),
    }
    
    successful_count = 0
    
    for data_type in data_types:
        if data_type not in backfill_functions:
            log_error(f"Unknown data type: {data_type}")
            continue
        
        log_info(f"\n--- Backfilling: {data_type} ---")
        
        try:
            success = backfill_functions[data_type]()
            if success:
                successful_count += 1
                log_success(f"✅ {data_type} completed successfully")
            else:
                log_error(f"❌ {data_type} failed")
        except Exception as e:
            log_error(f"❌ {data_type} failed with exception: {e}")
        
        time.sleep(1)
    
    log_info(f"\nSelective backfill completed: {successful_count}/{len(data_types)} successful")
    return successful_count == len(data_types)


def main():
    """Main entry point with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Historical Data Backfill Coordinator")
    
    parser.add_argument('--symbol', type=str, default=SYMBOL, help=f'Trading symbol (default: {SYMBOL})')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size (default: 1000)')
    
    # Date range options
    parser.add_argument('--last-week', action='store_true', help='Backfill only last week of data')
    parser.add_argument('--last-month', action='store_true', help='Backfill only last month of data')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD format)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD format)')
    
    # Selective backfill
    parser.add_argument('--data-types', nargs='+', 
                       choices=['ohlc', 'account', 'open_trades', 'closed_trades', 'market', 'max_gain_loss'],
                       help='Specific data types to backfill (selective mode)')
    
    # Options
    parser.add_argument('--skip-max-gain-loss', action='store_true', 
                       help='Skip max gain/loss calculations (complete mode only)')
    
    args = parser.parse_args()
    
    # Handle date range
    start_date = None
    end_date = None
    
    if args.last_week:
        end_date_obj = datetime.now(timezone.utc)
        start_date_obj = end_date_obj - timedelta(days=7)
        start_date = start_date_obj.strftime('%Y-%m-%d')
        end_date = end_date_obj.strftime('%Y-%m-%d')
    elif args.last_month:
        end_date_obj = datetime.now(timezone.utc)
        start_date_obj = end_date_obj - timedelta(days=30)
        start_date = start_date_obj.strftime('%Y-%m-%d')
        end_date = end_date_obj.strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
        end_date = args.end_date
    
    # Run backfill
    if args.data_types:
        # Selective backfill
        success = run_selective_backfill(args.symbol, args.data_types, start_date, end_date, args.batch_size)
    else:
        # Complete backfill
        success = run_complete_backfill(args.symbol, start_date, end_date, args.batch_size, args.skip_max_gain_loss)
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
