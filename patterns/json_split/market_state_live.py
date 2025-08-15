#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Market State Live Exporter - Feature 6.1
Exports live market state data to the database.

This script runs every minute and:
1. Fetches the latest M1 candle for volatility/spread calculation
2. Determines trading session based on UTC time
3. Builds market state JSON structure
4. Stores it in trading_snapshots.market_state_json column
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from common import (
    get_cursor, insert_snapshot, get_latest_m1_time,
    format_timestamp_utc, safe_float,
    log_info, log_error, log_success, SYMBOL
)


def get_trading_session(dt_utc: datetime) -> str:
    """
    Determine trading session based on UTC time.
    Based on your existing session_from_time function.
    
    London: 07:00–16:59 UTC
    NY:     13:00–20:59 UTC
    Other:  all other times
    """
    hour = dt_utc.hour
    if 7 <= hour <= 16:
        return "London"
    elif 13 <= hour <= 20:
        return "NY"
    else:
        return "Other"


def estimate_spread_from_candle(high: float, low: float) -> float:
    """
    Estimate spread from candle high/low.
    Based on your existing estimate_spread_from_candle function.
    """
    try:
        # 10% of candle range as conservative estimate, rounded to 2 decimals
        spread = (high - low) * 0.1
        return round(max(0.01, spread), 2)
    except Exception:
        return 0.40  # Fallback value


def fetch_latest_m1_candle(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch the latest M1 candle for market state calculation."""
    try:
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT open_time, high_price, low_price, atr
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1'
                ORDER BY open_time DESC
                LIMIT 1
            """, (symbol,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                "open_time": row["open_time"],
                "high": safe_float(row["high_price"]),
                "low": safe_float(row["low_price"]),
                "atr": safe_float(row["atr"])
            }
            
    except Exception as e:
        log_error(f"Failed to fetch latest M1 candle: {e}")
        return None


def calculate_market_state(candle: Dict[str, Any], reference_time: datetime) -> Dict[str, Any]:
    """
    Calculate market state based on latest M1 candle and time.
    Based on your existing market_state function.
    """
    try:
        # Volatility calculation
        atr = candle.get("atr", 0.0)
        if atr is None:
            atr = 0.0
        volatility = "high" if atr > 1.5 else "low"
        
        # Spread calculation
        high = candle.get("high", 0.0) or 0.0
        low = candle.get("low", 0.0) or 0.0
        spread = estimate_spread_from_candle(high, low)
        
        # Session detection
        session = get_trading_session(reference_time)
        
        # News event flag (always false for now, will be connected to API later)
        news_event = False
        
        return {
            "volatility": volatility,
            "spread": spread,
            "session": session,
            "news_event": news_event
        }
        
    except Exception as e:
        log_error(f"Failed to calculate market state: {e}")
        # Return default values
        return {
            "volatility": "low",
            "spread": 0.40,
            "session": "Other",
            "news_event": False
        }


def export_market_state_live(symbol: str = None) -> bool:
    """
    Export live market state to database.
    
    Args:
        symbol: Trading symbol (defaults to SYMBOL from environment)
        
    Returns:
        bool: True if successful, False otherwise
    """
    if symbol is None:
        symbol = SYMBOL
        
    log_info(f"Starting market state live export for {symbol}")
    
    try:
        # Get the latest M1 candle time for snapshot_time
        latest_m1_time = get_latest_m1_time(symbol)
        if not latest_m1_time:
            log_error("No M1 data found")
            return False
        
        # Fetch the latest M1 candle data
        candle = fetch_latest_m1_candle(symbol)
        if not candle:
            log_error("Failed to fetch latest M1 candle data")
            return False
        
        # Calculate market state
        market_state_data = calculate_market_state(candle, latest_m1_time)
        
        # The JSON structure is the market state data
        market_state_json = market_state_data
        
        # Insert into database
        success = insert_snapshot(
            symbol=symbol,
            snapshot_time=latest_m1_time,
            json_column_name="market_state_json",
            json_data=market_state_json
        )
        
        if success:
            log_success(f"Market state live export completed for {symbol}")
            log_info(f"Market state: {market_state_data}")
            return True
        else:
            log_error(f"Failed to insert market state data for {symbol}")
            return False
            
    except Exception as e:
        log_error(f"Market state live export failed: {e}")
        return False


def run_continuous(interval_seconds: int = 60):
    """
    Run the market state exporter continuously.
    
    Args:
        interval_seconds: Seconds between exports (default: 60 for 1 minute)
    """
    log_info(f"Starting continuous market state live export (interval: {interval_seconds}s)")
    
    while True:
        try:
            export_market_state_live()
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
        log_info("Running single market state export (use --continuous for continuous mode)")
        success = export_market_state_live()
        exit(0 if success else 1)
