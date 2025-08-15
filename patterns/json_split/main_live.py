#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSON Split Main Coordinator - Run All Live Exporters

This script coordinates all live exporters to run in sequence.
It can run once for testing or continuously for production.

Usage:
    python main_live.py              # Run once for testing
    python main_live.py --continuous # Run continuously every minute
    python main_live.py --test-db    # Test database connection only
"""

import sys
import time
import argparse
from datetime import datetime
from typing import List, Callable

from common import log_info, log_error, log_success, SYMBOL
from ohlc_all_live import export_ohlc_all_live
from account_state_live import export_account_state_live
from open_trades_live import export_open_trades_live
from closed_trades_live import export_closed_trades_live
from market_state_live import export_market_state_live


def test_database_connection():
    """Test database connection and basic functionality."""
    log_info("Testing database connection...")
    
    try:
        from common import get_cursor, get_latest_m1_time, get_latest_account_id
        
        # Test basic connection
        with get_cursor() as cur:
            cur.execute("SELECT version()")
            version_row = cur.fetchone()
            if version_row:
                if hasattr(version_row, 'keys'):  # RealDictCursor
                    version_text = str(list(version_row.values())[0])
                else:  # Regular cursor
                    version_text = str(version_row[0])
                log_success(f"Database connected: {version_text}")
            else:
                log_error("Could not get database version")
                return False
        
        # Test latest M1 time
        latest_m1 = get_latest_m1_time(SYMBOL)
        if latest_m1:
            log_success(f"Latest M1 time for {SYMBOL}: {latest_m1}")
        else:
            log_error(f"No M1 data found for {SYMBOL}")
            return False
        
        # Test latest account ID
        account_id = get_latest_account_id()
        if account_id:
            log_success(f"Latest account ID: {account_id}")
        else:
            log_error("No account data found")
            return False
        
        # Test trading_snapshots table structure
        with get_cursor() as cur:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'trading_snapshots' 
                AND column_name LIKE '%_json'
                ORDER BY column_name
            """)
            rows = cur.fetchall()
            json_columns = []
            for row in rows:
                if hasattr(row, 'keys'):  # RealDictCursor
                    json_columns.append(row['column_name'])
                else:  # Regular cursor
                    json_columns.append(row[0])
            
            expected_columns = [
                'ohlc_all_json', 'account_state_json', 'open_trades_json',
                'closed_trades_json', 'market_state_json'
            ]
            
            missing_columns = [col for col in expected_columns if col not in json_columns]
            if missing_columns:
                log_error(f"Missing JSON columns in trading_snapshots: {missing_columns}")
                log_info("Please run the update_schema.sql script first")
                return False
            else:
                log_success("All required JSON columns found in trading_snapshots table")
        
        return True
        
    except Exception as e:
        log_error(f"Database test failed: {e}")
        return False


def run_all_exporters(symbol: str = None) -> bool:
    """
    Run all live exporters in sequence.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        
    Returns:
        bool: True if all exporters succeeded, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
    
    exporters: List[Callable[[str], bool]] = [
        export_ohlc_all_live,
        export_account_state_live,
        export_open_trades_live,
        export_closed_trades_live,
        export_market_state_live
    ]
    
    exporter_names = [
        "OHLC All",
        "Account State", 
        "Open Trades",
        "Closed Trades",
        "Market State"
    ]
    
    log_info(f"Starting all live exporters for {symbol}")
    start_time = datetime.now()
    
    results = []
    for exporter, name in zip(exporters, exporter_names):
        try:
            log_info(f"Running {name} exporter...")
            success = exporter(symbol)
            results.append(success)
            
            if success:
                log_success(f"{name} exporter completed")
            else:
                log_error(f"{name} exporter failed")
                
        except Exception as e:
            log_error(f"{name} exporter crashed: {e}")
            results.append(False)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    successful_count = sum(results)
    total_count = len(results)
    
    if all(results):
        log_success(f"All {total_count} exporters completed successfully in {duration:.2f}s")
        return True
    else:
        log_error(f"Only {successful_count}/{total_count} exporters succeeded in {duration:.2f}s")
        return False


def run_continuous(interval_seconds: int = 60):
    """
    Run all exporters continuously.
    
    Args:
        interval_seconds: Seconds between export cycles (default: 60 for 1 minute)
    """
    log_info(f"Starting continuous JSON export cycle (interval: {interval_seconds}s)")
    log_info("Press Ctrl+C to stop")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            log_info(f"=== Export Cycle #{cycle_count} ===")
            
            success = run_all_exporters()
            
            if success:
                log_success(f"Cycle #{cycle_count} completed successfully")
            else:
                log_error(f"Cycle #{cycle_count} completed with errors")
            
        except KeyboardInterrupt:
            log_info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            log_error(f"Unexpected error in cycle #{cycle_count}: {e}")
        
        log_info(f"Waiting {interval_seconds} seconds for next cycle...")
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            log_info("Interrupt received during sleep, shutting down...")
            break


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Miando JSON Split Live Exporters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_live.py              # Run once for testing
  python main_live.py --continuous # Run continuously every minute  
  python main_live.py --test-db    # Test database connection only
  python main_live.py --interval 30 --continuous  # Run every 30 seconds
        """
    )
    
    parser.add_argument(
        '--continuous', 
        action='store_true',
        help='Run continuously (default: run once)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Interval in seconds between runs (default: 60)'
    )
    
    parser.add_argument(
        '--test-db',
        action='store_true', 
        help='Test database connection only'
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        default=SYMBOL,
        help=f'Trading symbol (default: {SYMBOL})'
    )
    
    args = parser.parse_args()
    
    # Test database connection first
    if not test_database_connection():
        log_error("Database test failed, exiting")
        sys.exit(1)
    
    if args.test_db:
        log_success("Database test completed successfully")
        sys.exit(0)
    
    # Run exporters
    if args.continuous:
        run_continuous(args.interval)
    else:
        log_info("Running single export cycle (use --continuous for continuous mode)")
        success = run_all_exporters(args.symbol)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
