#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Open Trades Live Exporter - Feature 3
Exports live open and pending trades to the database.

This script runs every minute and:
1. Fetches all currently open and pending trades
2. Retrieves original SL/TP from planned_trades
3. Builds open trades JSON structure
4. Stores it in trading_snapshots.open_trades_json column
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from common import (
    get_cursor, insert_snapshot, get_latest_m1_time, get_latest_account_id,
    format_timestamp_utc, safe_float, safe_int,
    log_info, log_error, log_success, SYMBOL
)


def fetch_original_sl_tp(magic_number: int) -> Tuple[Optional[float], Optional[float]]:
    """
    Fetch original SL and TP from planned_trades table.
    Based on your existing fetch_original_sl_tp function.
    """
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT sl, tp 
                FROM planned_trades
                WHERE magic_number = %s 
                AND sl IS NOT NULL AND tp IS NOT NULL
                ORDER BY timestamp ASC
                LIMIT 1
            """, (magic_number,))
            
            row = cur.fetchone()
            if not row:
                return None, None
                
            return safe_float(row["sl"]), safe_float(row["tp"])
            
    except Exception as e:
        log_error(f"Failed to fetch original SL/TP for magic {magic_number}: {e}")
        return None, None


def fetch_open_trades(account_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all open and pending trades for the given account_id.
    Based on your existing fetch_trades function.
    """
    trades = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT symbol, magic_number, order_type, lot_size, open_price, sl, tp, 
                       open_time, status, comment
                FROM open_trades
                WHERE account_id = %s AND status IN ('open', 'pending')
            """, (account_id,))
            
            rows = cur.fetchall()
            
            for row in rows:
                magic = safe_int(row["magic_number"])
                if magic is None:
                    log_error(f"Invalid magic number in trade: {row}")
                    continue
                
                # Get original SL and TP
                orig_sl, orig_tp = fetch_original_sl_tp(magic)
                
                trade = {
                    "symbol": row["symbol"],
                    "magic": magic,
                    "order_type": row["order_type"],
                    "lot_size": safe_float(row["lot_size"]),
                    "open_price": safe_float(row["open_price"]),
                    "sl": safe_float(row["sl"]),
                    "tp": safe_float(row["tp"]),
                    "open_time": format_timestamp_utc(row["open_time"]),
                    "status": row["status"],
                    "comment": row["comment"],
                    "original_sl": orig_sl,
                    "original_tp": orig_tp
                }
                trades.append(trade)
                
        log_info(f"Fetched {len(trades)} open/pending trades")
                
    except Exception as e:
        log_error(f"Failed to fetch open trades: {e}")
        
    return trades


def export_open_trades_live(symbol: str = None) -> bool:
    """
    Export live open trades to database.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
        
    log_info(f"Starting open trades live export for {symbol}")
    
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
        
        # Fetch open trades data
        trades_data = fetch_open_trades(account_id)
        
        # The JSON structure is an array of trades (even if empty)
        open_trades_json = trades_data
        
        # Insert into database
        success = insert_snapshot(
            symbol=symbol,
            snapshot_time=latest_m1_time,
            json_column_name="open_trades_json",
            json_data=open_trades_json
        )
        
        if success:
            log_success(f"Open trades live export completed for {symbol}")
            log_info(f"Exported {len(trades_data)} open/pending trades")
            return True
        else:
            log_error(f"Failed to insert open trades data for {symbol}")
            return False
            
    except Exception as e:
        log_error(f"Open trades live export failed: {e}")
        return False


def run_continuous(interval_seconds: int = 60):
    """
    Run the open trades exporter continuously.
    
    Args:
        interval_seconds: Seconds between exports (default: 60 for 1 minute)
    """
    log_info(f"Starting continuous open trades live export (interval: {interval_seconds}s)")
    
    while True:
        try:
            export_open_trades_live()
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
        log_info("Running single open trades export (use --continuous for continuous mode)")
        success = export_open_trades_live()
        exit(0 if success else 1)
