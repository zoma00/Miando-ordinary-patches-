#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pattern JSON Live Exporter - Optimized Feature 1
Exports compact OHLC data optimized for vector matching and pattern analysis.

This script runs every minute and:
1. Fetches limited OHLC data + indicators for pattern matching (compact counts)
2. Includes key indicators optimized for vectorization 
3. Integrates 1-hour outcome data for direct setup-to-result linking
4. Stores in trading_snapshots.pattern_json column
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import psycopg2.extras

from common import (
    get_cursor, insert_snapshot, get_latest_m1_time, get_pg_conn,
    format_timestamp_utc, safe_float, safe_float_nullable, safe_int,
    log_info, log_error, log_success, SYMBOL
)

# Optimized timeframe configurations for pattern matching
PATTERN_TIMEFRAME_LIMITS = {
    "D1": 7,    # ~1 trading week - Mid-term trend without excessive history
    "H4": 5,    # ~1 day - Intraday trend + possible reversals  
    "H1": 20,   # ~20 hours - Previous day + current session context
    "M15": 30,  # ~7.5 hours - Smaller intraday moves & structure
    "M5": 30,   # ~2.5 hours - Entry/exit fine-tuning
    "M1": 60    # 1 hour - Immediate pre-trade pattern
}

# Key indicators for pattern matching (optimized for vector size)
KEY_INDICATORS = ['rsi', 'ema', 'atr', 'bb_middle', 'bb_upper', 'bb_lower']


def fetch_pattern_ohlc_for_timeframe(symbol: str, timeframe: str, limit: int) -> List[Dict[str, Any]]:
    """
    Fetch compact OHLC data optimized for pattern matching.
    Returns only essential candle data with key indicators.
    """
    candles = []
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Query optimized for pattern matching - only key indicators
            cur.execute("""
                SELECT 
                    open_time, open_price, high_price, low_price, close_price, volume,
                    rsi, ema, atr, bb_middle, bb_upper, bb_lower
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = %s
                ORDER BY open_time DESC
                LIMIT %s
            """, (symbol, timeframe, limit))
            
            rows = cur.fetchall()
            
            # Convert to compact structure, sorted oldest first
            for row in reversed(rows):
                candle = {
                    "open_time": format_timestamp_utc(row["open_time"]),
                    "open": safe_float(row["open_price"]),
                    "high": safe_float(row["high_price"]),
                    "low": safe_float(row["low_price"]),
                    "close": safe_float(row["close_price"]),
                    "volume": safe_int(row["volume"]),
                    # Key indicators - use nullable version to preserve None values
                    "rsi": safe_float_nullable(row["rsi"]),
                    "ema": safe_float_nullable(row["ema"]),
                    "atr": safe_float_nullable(row["atr"]),
                    "bb_middle": safe_float_nullable(row["bb_middle"]),
                    "bb_upper": safe_float_nullable(row["bb_upper"]),
                    "bb_lower": safe_float_nullable(row["bb_lower"]),
                }
                candles.append(candle)
                
        log_info(f"Fetched {len(candles)} pattern candles for {timeframe}")
                
    except Exception as e:
        log_error(f"Failed to fetch pattern {timeframe} data: {e}")
        
    return candles


def get_latest_indicator_values(symbol: str) -> Dict[str, Dict[str, float]]:
    """
    Get latest indicator values for all timeframes.
    Returns structured indicators optimized for pattern matching.
    """
    indicators = {}
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            for timeframe in PATTERN_TIMEFRAME_LIMITS.keys():
                cur.execute("""
                    SELECT rsi, ema, atr
                    FROM ohlc_data
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY open_time DESC
                    LIMIT 1
                """, (symbol, timeframe))
                
                row = cur.fetchone()
                if row:
                    if 'rsi' not in indicators:
                        indicators['rsi'] = {}
                    if 'ema' not in indicators:
                        indicators['ema'] = {}
                    if 'atr' not in indicators:
                        indicators['atr'] = {}
                        
                    indicators['rsi'][timeframe] = safe_float_nullable(row['rsi'])
                    indicators['ema'][timeframe] = safe_float_nullable(row['ema'])
                    indicators['atr'][timeframe] = safe_float_nullable(row['atr'])
                    
    except Exception as e:
        log_error(f"Failed to get indicator values: {e}")
        
    return indicators


def calculate_1h_outcome(symbol: str, snapshot_time: datetime) -> Dict[str, float]:
    """
    Calculate 1-hour outcome from snapshot time.
    Returns max gain/loss percentages for pattern evaluation.
    """
    outcome = {
        "max_gain_pct_1h": None,
        "max_loss_pct_1h": None
    }
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get current price at snapshot time
            cur.execute("""
                SELECT close_price
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1' 
                AND open_time <= %s
                ORDER BY open_time DESC
                LIMIT 1
            """, (symbol, snapshot_time))
            
            current_row = cur.fetchone()
            if not current_row:
                return outcome
                
            current_price = safe_float(current_row['close_price'])
            if current_price == 0.0:
                return outcome
            
            # Get all M1 candles in the next hour
            end_time = snapshot_time + timedelta(hours=1)
            cur.execute("""
                SELECT high_price, low_price
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1'
                AND open_time > %s AND open_time <= %s
                ORDER BY open_time ASC
            """, (symbol, snapshot_time, end_time))
            
            rows = cur.fetchall()
            if not rows:
                return outcome
            
            max_high = max(safe_float(row['high_price']) for row in rows)
            min_low = min(safe_float(row['low_price']) for row in rows)
            
            # Calculate percentage gains/losses
            if max_high > current_price:
                outcome["max_gain_pct_1h"] = round(((max_high - current_price) / current_price) * 100, 2)
            
            if min_low < current_price:
                outcome["max_loss_pct_1h"] = round(((min_low - current_price) / current_price) * 100, 2)
                
    except Exception as e:
        log_error(f"Failed to calculate 1h outcome: {e}")
        
    return outcome


def calculate_spread_from_latest_m1(symbol: str, snapshot_time: datetime, force_fresh: bool = False) -> float:
    """
    Calculate spread from latest M1 candle following Hazem's requirements:
    - Always use latest available M1 candle
    - Ensure spread is never negative and has 2 decimal places
    - Calculate as 10% of candle range (high - low)
    
    Args:
        symbol: Trading symbol (e.g., 'XAUUSD')
        snapshot_time: Timestamp for reference
        force_fresh: If True, forces a fresh database connection to get latest data
    """
    try:
        if force_fresh:
            # Force fresh connection to get absolute latest M1 data
            conn = None
            try:
                conn = get_pg_conn()
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Get absolute latest M1 candle regardless of snapshot_time
                    cur.execute("""
                        SELECT high_price, low_price, open_time, NOW() as query_time
                        FROM ohlc_data
                        WHERE symbol = %s AND timeframe = 'M1'
                        ORDER BY open_time DESC
                        LIMIT 1
                    """, (symbol,))
                    
                    candle = cur.fetchone()
                    if not candle:
                        return 0.40  # Fallback spread value
                    
                    print(f"[INFO] Fresh spread calculation from M1 at {candle['open_time']}")
                    
                    # Convert Decimal to float and calculate spread as 10% of candle range
                    high_price = float(candle['high_price'])
                    low_price = float(candle['low_price'])
                    spread = (high_price - low_price) * 0.1
                    
                    # Ensure positive and 2 decimal places (per your requirements)
                    return round(max(0.01, spread), 2)
            finally:
                if conn:
                    conn.close()
        else:
            # Standard approach with snapshot_time reference
            with get_cursor(dict_cursor=True) as cur:
                cur.execute("""
                    SELECT high_price, low_price
                    FROM ohlc_data
                    WHERE symbol = %s AND timeframe = 'M1'
                    AND open_time <= %s
                    ORDER BY open_time DESC
                    LIMIT 1
                """, (symbol, snapshot_time))
                
                candle = cur.fetchone()
                if not candle:
                    return 0.40  # Fallback spread value
                
                # Convert Decimal to float and calculate spread as 10% of candle range
                high_price = float(candle['high_price'])
                low_price = float(candle['low_price'])
                spread = (high_price - low_price) * 0.1
                
                # Ensure positive and 2 decimal places (per your requirements)
                return round(max(0.01, spread), 2)
            
    except Exception as e:
        log_error(f"Failed to calculate spread: {e}")
        return 0.40  # Fallback spread value


def get_trading_session(snapshot_time: datetime) -> str:
    """
    Determine trading session based on UTC time.
    
    Corrected session mapping:
    - Sydney: 22:00 UTC - 06:59 UTC (next day)
    - London: 07:00 UTC - 14:59 UTC  
    - New York: 15:00 UTC - 21:59 UTC
    """
    hour = snapshot_time.hour
    
    # Trading sessions in UTC (corrected)
    if 22 <= hour <= 23 or 0 <= hour <= 6:
        return "Sydney"
    elif 7 <= hour <= 14:
        return "London" 
    elif 15 <= hour <= 21:
        return "New York"
    else:
        return "Unknown"


def assess_volatility(atr_values: Dict[str, float], price_metrics: Dict[str, Any] = None) -> str:
    """
    Enhanced volatility assessment using multiple ATR timeframes and XAUUSD-specific thresholds.
    Falls back to price range analysis if ATR data is unavailable.
    """
    # Try multiple timeframes in order of preference
    timeframes_to_check = ['H1', 'H4', 'M15', 'M5']
    
    for timeframe in timeframes_to_check:
        if timeframe in atr_values and atr_values[timeframe] is not None:
            atr_value = atr_values[timeframe]
            
            # XAUUSD-specific volatility thresholds (Gold is more volatile than forex)
            if timeframe == 'H1':
                if atr_value > 15.0:    # Gold H1 ATR > $15 = high volatility
                    return "high"
                elif atr_value > 8.0:   # Gold H1 ATR > $8 = medium volatility  
                    return "medium"
                else:
                    return "low"
                    
            elif timeframe == 'H4':
                if atr_value > 25.0:    # Gold H4 ATR > $25 = high volatility
                    return "high"
                elif atr_value > 12.0:  # Gold H4 ATR > $12 = medium volatility
                    return "medium"
                else:
                    return "low"
                    
            elif timeframe == 'M15':
                if atr_value > 6.0:     # Gold M15 ATR > $6 = high volatility
                    return "high"
                elif atr_value > 3.0:   # Gold M15 ATR > $3 = medium volatility
                    return "medium"
                else:
                    return "low"
                    
            elif timeframe == 'M5':
                if atr_value > 3.0:     # Gold M5 ATR > $3 = high volatility
                    return "high"
                elif atr_value > 1.5:   # Gold M5 ATR > $1.5 = medium volatility
                    return "medium"
                else:
                    return "low"
    
    # Fallback: Use price range analysis when ATR data is unavailable
    if price_metrics:
        # Use 4-hour range as primary fallback (more stable than 1h)
        if price_metrics.get("price_range_4h"):
            range_4h = price_metrics["price_range_4h"]
            if range_4h > 20.0:      # Gold 4h range > $20 = high volatility
                return "high_price"
            elif range_4h > 10.0:    # Gold 4h range > $10 = medium volatility
                return "medium_price" 
            else:
                return "low_price"
        
        # Secondary fallback: Use 1-hour range
        elif price_metrics.get("price_range_1h"):
            range_1h = price_metrics["price_range_1h"]
            if range_1h > 8.0:       # Gold 1h range > $8 = high volatility
                return "high_price"
            elif range_1h > 4.0:     # Gold 1h range > $4 = medium volatility
                return "medium_price"
            else:
                return "low_price"
    
    return "no_data"  # No ATR or price data available


def calculate_price_volatility(symbol: str, snapshot_time: datetime) -> Dict[str, Any]:
    """
    Calculate additional volatility metrics from recent price movement.
    """
    volatility_info = {
        "price_range_1h": None,
        "price_range_4h": None,
        "volatility_percentile": None
    }
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Calculate 1-hour price range
            hour_ago = snapshot_time - timedelta(hours=1)
            cur.execute("""
                SELECT MIN(low_price) as min_low, MAX(high_price) as max_high
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1'
                AND open_time BETWEEN %s AND %s
            """, (symbol, hour_ago, snapshot_time))
            
            hour_row = cur.fetchone()
            if hour_row and hour_row['min_low'] and hour_row['max_high']:
                volatility_info["price_range_1h"] = round(
                    float(hour_row['max_high']) - float(hour_row['min_low']), 2
                )
            
            # Calculate 4-hour price range
            four_hours_ago = snapshot_time - timedelta(hours=4)
            cur.execute("""
                SELECT MIN(low_price) as min_low, MAX(high_price) as max_high
                FROM ohlc_data
                WHERE symbol = %s AND timeframe = 'M1'
                AND open_time BETWEEN %s AND %s
            """, (symbol, four_hours_ago, snapshot_time))
            
            four_hour_row = cur.fetchone()
            if four_hour_row and four_hour_row['min_low'] and four_hour_row['max_high']:
                volatility_info["price_range_4h"] = round(
                    float(four_hour_row['max_high']) - float(four_hour_row['min_low']), 2
                )
    
    except Exception as e:
        log_error(f"Failed to calculate price volatility: {e}")
    
    return volatility_info


def build_pattern_json(symbol: str, force_fresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Build optimized pattern JSON for vector matching.
    
    Args:
        symbol: Trading symbol (e.g., 'XAUUSD')
        force_fresh: If True, forces fresh database connections to bypass caching
    """
    try:
        # Get snapshot time (latest M1 candle time)
        latest_m1_time = get_latest_m1_time(symbol, force_fresh=force_fresh)
        if not latest_m1_time:
            log_error("No M1 data available")
            return None
            
        if force_fresh:
            log_info(f"🔄 Building FRESH pattern JSON for {symbol} at {latest_m1_time}")
        else:
            log_info(f"Building pattern JSON for {symbol} at {latest_m1_time}")
        
        # Fetch compact candle data for all timeframes
        context = {}
        for timeframe, limit in PATTERN_TIMEFRAME_LIMITS.items():
            candles = fetch_pattern_ohlc_for_timeframe(symbol, timeframe, limit)
            context[timeframe] = candles
            
        # Get latest indicator values
        indicators = get_latest_indicator_values(symbol)
        
        # Calculate 1-hour outcome
        outcome_1h = calculate_1h_outcome(symbol, latest_m1_time)
        
        # Determine session and enhanced volatility analysis
        session = get_trading_session(latest_m1_time)
        
        # Calculate spread from latest M1 candle (per Hazem's requirements)
        spread = calculate_spread_from_latest_m1(symbol, latest_m1_time, force_fresh=force_fresh)
        
        # Calculate additional price-based volatility metrics
        price_volatility = calculate_price_volatility(symbol, latest_m1_time)
        
        # Assess volatility with fallback to price metrics
        volatility = assess_volatility(indicators.get('atr', {}), price_volatility)
        
        # Build compact pattern JSON with spread integration
        pattern_json = {
            "symbol": symbol,
            "snapshot_time": format_timestamp_utc(latest_m1_time),
            "context": context,
            "indicators": indicators,
            "outcome_1h": outcome_1h,
            "session": session,
            "volatility": volatility,
            "volatility_metrics": price_volatility,
            "spread": spread,  # Added spread calculation per Hazem's requirements
            "news_event": False  # Placeholder for future news API integration
        }
        
        log_success(f"Built pattern JSON with {len(context)} timeframes")
        return pattern_json
        
    except Exception as e:
        log_error(f"Failed to build pattern JSON: {e}")
        return None


def store_pattern_json(symbol: str, snapshot_time: datetime, pattern_json: Dict[str, Any]) -> bool:
    """
    Store pattern JSON in database.
    """
    try:
        import json
        
        with get_cursor() as cur:
            # Convert dict to JSON string for JSONB storage
            json_string = json.dumps(pattern_json)
            
            # Insert or update pattern JSON - provide snapshot_json as well since it's NOT NULL
            cur.execute("""
                INSERT INTO trading_snapshots (symbol, snapshot_time, snapshot_json, pattern_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (symbol, snapshot_time) 
                DO UPDATE SET 
                    pattern_json = EXCLUDED.pattern_json,
                    snapshot_json = EXCLUDED.snapshot_json
            """, (symbol, snapshot_time, json_string, json_string))
            
        log_success(f"Stored pattern JSON for {symbol}")
        return True
        
    except Exception as e:
        log_error(f"Failed to store pattern JSON: {e}")
        return False


def main():
    """
    Main execution function - run every minute.
    Supports --force-fresh command line argument to bypass caching.
    """
    import sys
    
    # Check for force-fresh flag
    force_fresh = "--force-fresh" in sys.argv
    
    if force_fresh:
        log_info("🔄 Starting Pattern JSON Live Export with FORCE FRESH mode...")
    else:
        log_info("Starting Pattern JSON Live Export...")
    
    try:
        # Build pattern JSON
        pattern_json = build_pattern_json(SYMBOL, force_fresh=force_fresh)
        if not pattern_json:
            log_error("Failed to build pattern JSON")
            return
            
        # Store in database
        snapshot_time = datetime.fromisoformat(pattern_json["snapshot_time"].replace('Z', '+00:00'))
        success = store_pattern_json(SYMBOL, snapshot_time, pattern_json)
        
        if success:
            if force_fresh:
                log_success("✅ FRESH Pattern JSON export completed successfully")
            else:
                log_success("Pattern JSON export completed successfully")
        else:
            log_error("Pattern JSON export failed")
            
    except Exception as e:
        log_error(f"Pattern JSON export error: {e}")


if __name__ == "__main__":
    main()
