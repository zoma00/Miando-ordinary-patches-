#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OHLC All Live Exporter - Feature 1
Exports live OHLC data with indicators for all timeframes to the database.

This script runs every minute and:
1. Fetches OHLC data + indicators for all timeframes (M1, M5, M15, H1, H4, D1)
2. Builds a comprehensive JSON structure
3. Stores it in trading_snapshots.ohlc_all_json column
"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from common import (
    get_cursor, insert_snapshot, get_latest_m1_time, 
    format_timestamp_utc, safe_float, safe_int,
    log_info, log_error, log_success, SYMBOL
)

# Timeframe configurations - matching Amir's requirements
TIMEFRAME_LIMITS = {
    "M1": 120,   # ~2 hours
    "M5": 288,   # 1 day  
    "M15": 192,  # 2 days
    "H1": 480,   # 20 days
    "H4": 300,   # ~2 months
    "D1": 250    # ~1 year
}


def fetch_ohlc_for_timeframe(symbol: str, timeframe: str, limit: int) -> List[Dict[str, Any]]:
    """
    Fetch OHLC data for a specific timeframe, based on your current DB structure.
    Returns candles sorted oldest to newest.
    """
    candles = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Query based on your existing database structure
            cur.execute("""
                SELECT 
                    open_time, open_price, high_price, low_price, close_price, volume,
                    adx, atr, bb_middle, bb_upper, bb_lower, cci, ema,
                    macd, macd_signal, macd_hist, obv, rsi, sma,
                    stochastic_k, stochastic_d, willr
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = %s
                ORDER BY open_time DESC
                LIMIT %s
            """, (symbol, timeframe, limit))
            
            rows = cur.fetchall()
            
            # Convert to list of dicts, sorted oldest first (reverse the DESC order)
            for row in reversed(rows):
                candle = {
                    "open_time": format_timestamp_utc(row["open_time"]),
                    "open": safe_float(row["open_price"]),
                    "high": safe_float(row["high_price"]),
                    "low": safe_float(row["low_price"]),
                    "close": safe_float(row["close_price"]),
                    "volume": safe_int(row["volume"]),
                    "adx": safe_float(row["adx"]),
                    "atr": safe_float(row["atr"]),
                    "bb_middle": safe_float(row["bb_middle"]),
                    "bb_upper": safe_float(row["bb_upper"]),
                    "bb_lower": safe_float(row["bb_lower"]),
                    "cci": safe_float(row["cci"]),
                    "ema": safe_float(row["ema"]),
                    "macd": safe_float(row["macd"]),
                    "macd_signal": safe_float(row["macd_signal"]),
                    "macd_hist": safe_float(row["macd_hist"]),
                    "obv": safe_float(row["obv"]),
                    "rsi": safe_float(row["rsi"]),
                    "sma": safe_float(row["sma"]),
                    "stoch_k": safe_float(row["stochastic_k"]),
                    "stoch_d": safe_float(row["stochastic_d"]),
                    "willr": safe_float(row["willr"]),
                }
                candles.append(candle)
                
        log_info(f"Fetched {len(candles)} candles for {timeframe}")
                
    except Exception as e:
        log_error(f"Failed to fetch {timeframe} data: {e}")
        
    return candles


def build_ohlc_last_time(timeframes_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    """Build the ohlc_last_time dictionary from timeframes data."""
    last_times = {}
    
    for timeframe, candles in timeframes_data.items():
        if candles:
            # Get the most recent candle (last in list since sorted oldest to newest)
            last_times[timeframe] = candles[-1]["open_time"]
        else:
            last_times[timeframe] = None
            
    return last_times


def export_ohlc_all_live(symbol: str = None) -> bool:
    """
    Export live OHLC data for all timeframes to database.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
        
    log_info(f"Starting OHLC live export for {symbol}")
    
    try:
        # Get the latest M1 candle time for snapshot_time
        latest_m1_time = get_latest_m1_time(symbol)
        if not latest_m1_time:
            log_error("No M1 data found")
            return False
        
        # Fetch data for all timeframes
        timeframes_data = {}
        for timeframe, limit in TIMEFRAME_LIMITS.items():
            candles = fetch_ohlc_for_timeframe(symbol, timeframe, limit)
            timeframes_data[timeframe] = candles
        
        # Build the ohlc_last_time structure
        ohlc_last_time = build_ohlc_last_time(timeframes_data)
        
        # Build the JSON structure matching Amir's specification
        ohlc_json = {
            "symbol": symbol,
            "timestamp": format_timestamp_utc(latest_m1_time),
            "ohlc": timeframes_data,  # Note: using "ohlc" not "timeframes" to match spec
            "ohlc_last_time": ohlc_last_time,
            "last_update": format_timestamp_utc(latest_m1_time)
        }
        
        # Insert into database
        success = insert_snapshot(
            symbol=symbol,
            snapshot_time=latest_m1_time,
            json_column_name="ohlc_all_json",
            json_data=ohlc_json
        )
        
        if success:
            log_success(f"OHLC live export completed for {symbol}")
            return True
        else:
            log_error(f"Failed to insert OHLC data for {symbol}")
            return False
            
    except Exception as e:
        log_error(f"OHLC live export failed: {e}")
        return False


def run_continuous(interval_seconds: int = 60):
    """
    Run the OHLC exporter continuously.
    
    Args:
        interval_seconds: Seconds between exports (default: 60 for 1 minute)
    """
    log_info(f"Starting continuous OHLC live export (interval: {interval_seconds}s)")
    
    while True:
        try:
            export_ohlc_all_live()
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
        log_info("Running single OHLC export (use --continuous for continuous mode)")
        success = export_ohlc_all_live()
        exit(0 if success else 1)
