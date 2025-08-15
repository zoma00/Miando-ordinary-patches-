#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Account State Live Exporter - Feature 5
Exports live account state data to the database.

This script runs every minute and:
1. Fetches the latest account state (balance, equity, margin, etc.)
2. Builds account state JSON structure
3. Stores it in trading_snapshots.account_state_json column
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from common import (
    get_cursor, insert_snapshot, get_latest_m1_time, get_latest_account_id,
    format_timestamp_utc, safe_float, safe_int,
    log_info, log_error, log_success, SYMBOL
)


def fetch_account_state(account_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest account state for the given account_id.
    Based on your existing fetch_account_state function.
    """
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT timestamp, balance, equity, margin, free_margin, 
                       leverage, profit, currency
                FROM account_state 
                WHERE account_id = %s 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (account_id,))
            
            row = cur.fetchone()
            if not row:
                log_error(f"No account state found for account_id: {account_id}")
                return None
            
            return {
                "timestamp": format_timestamp_utc(row["timestamp"]),
                "balance": safe_float(row["balance"]),
                "equity": safe_float(row["equity"]),
                "margin": safe_float(row["margin"]),
                "free_margin": safe_float(row["free_margin"]),
                "leverage": safe_int(row["leverage"]),
                "profit": safe_float(row["profit"]),
                "currency": row["currency"]
            }
            
    except Exception as e:
        log_error(f"Failed to fetch account state: {e}")
        return None


def export_account_state_live(symbol: str = None) -> bool:
    """
    Export live account state to database.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
        
    log_info(f"Starting account state live export for {symbol}")
    
    try:
        # Get the latest account ID
        account_id = get_latest_account_id()
        if not account_id:
            log_error("No account_id found")
            return False
        
        # Get the latest M1 candle time for snapshot_time
        latest_m1_time = get_latest_m1_time(symbol)
        if not latest_m1_time:
            log_error("No M1 data found")
            return False
        
        # Fetch account state data
        account_data = fetch_account_state(account_id)
        if not account_data:
            log_error("Failed to fetch account state data")
            return False
        
        # The JSON structure is exactly the account state data
        account_state_json = account_data
        
        # Insert into database
        success = insert_snapshot(
            symbol=symbol,
            snapshot_time=latest_m1_time,
            json_column_name="account_state_json",
            json_data=account_state_json
        )
        
        if success:
            log_success(f"Account state live export completed for {symbol}")
            log_info(f"Account balance: {account_data.get('balance')}, equity: {account_data.get('equity')}")
            return True
        else:
            log_error(f"Failed to insert account state data for {symbol}")
            return False
            
    except Exception as e:
        log_error(f"Account state live export failed: {e}")
        return False


def run_continuous(interval_seconds: int = 60):
    """
    Run the account state exporter continuously.
    
    Args:
        interval_seconds: Seconds between exports (default: 60 for 1 minute)
    """
    log_info(f"Starting continuous account state live export (interval: {interval_seconds}s)")
    
    while True:
        try:
            export_account_state_live()
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
        log_info("Running single account state export (use --continuous for continuous mode)")
        success = export_account_state_live()
        exit(0 if success else 1)
