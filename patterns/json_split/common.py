#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Common database helper functions for JSON split functionality.
Provides database connection, snapshot insertion, and utility functions.
"""

import os
import time
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from psycopg2 import OperationalError

# Database configuration from environment variables
# Auto-detect host vs container environment
def _get_db_host():
    """Auto-detect appropriate database host based on environment."""
    if os.getenv('DB_HOST'):
        return os.getenv('DB_HOST')
    # Check if running in container (common container indicators)
    if os.path.exists('/.dockerenv') or os.getenv('HOSTNAME', '').startswith(('patterns', 'json')):
        return 'miando-db'  # Container hostname
    else:
        return 'localhost'  # Host system

def _get_db_port():
    """Auto-detect appropriate database port based on environment.""" 
    if os.getenv('DB_PORT'):
        return os.getenv('DB_PORT')
    # Check if running in container
    if os.path.exists('/.dockerenv') or os.getenv('HOSTNAME', '').startswith(('patterns', 'json')):
        return '5432'  # Internal container port
    else:
        return '5434'  # Host mapped port

DB_CONFIG = {
    "host": _get_db_host(),
    "port": _get_db_port(),
    "database": os.getenv('DB_NAME', 'miando'),
    "user": os.getenv('DB_USER', 'miando'),
    "password": os.getenv('DB_PASSWORD', 'changeme'),
    # Temporarily disable SSL for testing
    # "sslmode": 'require',
    # "sslcert": '/app/server.crt',
    # "sslkey": '/app/server.key'
}

# Default symbol
SYMBOL = os.getenv('SYMBOL', 'XAUUSD')


def get_pg_conn(max_retries: int = 5, backoff_seconds: float = 1.5):
    """
    Get PostgreSQL connection with autocommit enabled.
    Includes retry logic for database connection failures.
    """
    # Debug: Show connection info on first connection attempt
    if not hasattr(get_pg_conn, '_logged'):
        print(f"[INFO] Connecting to database: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        get_pg_conn._logged = True
        
    attempt = 0
    while True:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            return conn
        except OperationalError as e:
            attempt += 1
            if attempt > max_retries:
                print(f"[ERROR] Failed to connect to database after {max_retries} attempts: {e}")
                raise
            print(f"[WARNING] Database connection attempt {attempt} failed, retrying in {backoff_seconds * attempt}s...")
            time.sleep(backoff_seconds * attempt)


@contextmanager
def get_cursor(dict_cursor: bool = True):
    """
    Context manager for database cursor with automatic connection handling.
    """
    conn = None
    try:
        conn = get_pg_conn()
        cursor_factory = psycopg2.extras.RealDictCursor if dict_cursor else None
        cur = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cur
        finally:
            cur.close()
    except Exception as e:
        print(f"[ERROR] Database operation failed: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def insert_snapshot(
    symbol: str,
    snapshot_time: datetime,
    json_column_name: str,
    json_data: Dict[str, Any],
    extra_columns: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Insert or update a snapshot in trading_snapshots table.
    
    Args:
        symbol: Trading symbol (e.g., "XAUUSD")
        snapshot_time: Timestamp for the snapshot
        json_column_name: Name of the JSON column to update
        json_data: JSON data to store
        extra_columns: Additional columns to update (for ohlc calculations)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_cursor(dict_cursor=False) as cur:
            # Ensure snapshot_time is UTC
            if snapshot_time.tzinfo is None:
                snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)
            elif snapshot_time.tzinfo != timezone.utc:
                snapshot_time = snapshot_time.astimezone(timezone.utc)
            
            # Build the query dynamically
            set_clauses = [f"{json_column_name} = %s"]
            values = [json.dumps(json_data)]
            
            if extra_columns:
                for col, val in extra_columns.items():
                    set_clauses.append(f"{col} = %s")
                    values.append(val)
            
            set_clause = ", ".join(set_clauses)
            
            # Use INSERT ... ON CONFLICT for upsert functionality
            # Include snapshot_json with empty object to satisfy NOT NULL constraint
            query = f"""
            INSERT INTO trading_snapshots (symbol, snapshot_time, snapshot_json, {json_column_name})
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (symbol, snapshot_time) 
            DO UPDATE SET {set_clause}
            """
            
            # Combine all values (add empty JSON object for snapshot_json)
            all_values = [symbol, snapshot_time, '{}', json.dumps(json_data)] + values
            
            cur.execute(query, all_values)
            print(f"[INFO] Updated {json_column_name} for {symbol} at {snapshot_time}")
            return True
            
    except Exception as e:
        print(f"[ERROR] Failed to insert snapshot: {e}")
        return False


def get_latest_m1_time(symbol: str, force_fresh: bool = False) -> Optional[datetime]:
    """
    Get the timestamp of the latest M1 candle for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., 'XAUUSD')
        force_fresh: If True, forces a fresh database connection and bypasses any caching
    """
    try:
        if force_fresh:
            # Force fresh connection to bypass any caching issues
            conn = None
            try:
                conn = get_pg_conn()
                # Use a fresh cursor with no caching
                with conn.cursor() as cur:
                    # Add NOW() to ensure fresh query execution
                    cur.execute("""
                        SELECT open_time, NOW() as current_time
                        FROM ohlc_data 
                        WHERE symbol = %s AND timeframe = 'M1'
                        ORDER BY open_time DESC 
                        LIMIT 1
                    """, (symbol,))
                    
                    row = cur.fetchone()
                    if row:
                        timestamp = row[0]
                        current_time = row[1]
                        print(f"[INFO] Fresh query executed at {current_time}, latest M1: {timestamp}")
                        
                        # Ensure UTC timezone
                        if hasattr(timestamp, 'astimezone'):
                            return timestamp.astimezone(timezone.utc)
                        else:
                            return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp
                    return None
            finally:
                if conn:
                    conn.close()
        else:
            # Standard cached approach
            with get_cursor(dict_cursor=False) as cur:
                cur.execute("""
                    SELECT open_time 
                    FROM ohlc_data 
                    WHERE symbol = %s AND timeframe = 'M1'
                    ORDER BY open_time DESC 
                    LIMIT 1
                """, (symbol,))
                
                row = cur.fetchone()
                if row:
                    timestamp = row[0]
                    # Ensure UTC timezone
                    if hasattr(timestamp, 'astimezone'):
                        return timestamp.astimezone(timezone.utc)
                    else:
                        return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp
                return None
            
    except Exception as e:
        print(f"[ERROR] Failed to get latest M1 time: {e}")
        return None


def get_latest_account_id() -> Optional[str]:
    """Get the most recent account_id from account_state table."""
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                SELECT account_id 
                FROM account_state 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            row = cur.fetchone()
            return str(row[0]) if row else None
            
    except Exception as e:
        print(f"[ERROR] Failed to get latest account_id: {e}")
        return None


def format_timestamp_utc(dt: Union[datetime, str]) -> Optional[str]:
    """
    Format datetime to UTC ISO string.
    
    Args:
        dt: datetime object or string
        
    Returns:
        str: ISO formatted UTC timestamp, or None if input is None
    """
    if dt is None:
        return None
    
    if isinstance(dt, str):
        return dt
    
    if hasattr(dt, 'astimezone'):
        return dt.astimezone(timezone.utc).isoformat()
    else:
        return str(dt)


def safe_float(value: Any) -> float:
    """Safely convert value to float, return 0.0 if conversion fails."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def safe_float_nullable(value: Any) -> Optional[float]:
    """Safely convert value to float, return None for missing indicators."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> int:
    """Safely convert value to int, return 0 if conversion fails."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def log_info(message: str) -> None:
    """Log info message with timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [INFO] {message}")


def log_error(message: str) -> None:
    """Log error message with timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [ERROR] {message}")


def log_success(message: str) -> None:
    """Log success message with timestamp."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [SUCCESS] {message}")


def validate_pattern_json_quality(symbol: str = 'XAUUSD') -> None:
    """
    Comprehensive validation of Pattern JSON data quality.
    Checks all the requirements from your checklist.
    """
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get the latest pattern JSON
            cur.execute("""
                SELECT 
                    symbol,
                    snapshot_time,
                    pattern_json,
                    jsonb_pretty(pattern_json) as pretty_json
                FROM trading_snapshots
                WHERE symbol = %s AND pattern_json IS NOT NULL
                ORDER BY snapshot_time DESC
                LIMIT 1
            """, (symbol,))
            
            row = cur.fetchone()
            if not row:
                log_error(f"No pattern JSON found for {symbol}")
                return
            
            pattern_json = row['pattern_json']
            snapshot_time = row['snapshot_time']
            
            log_info(f"Validating Pattern JSON for {symbol} at {snapshot_time}")
            print("=" * 60)
            
            # 1. Check volatility assessment vs ATR rule
            volatility = pattern_json.get('volatility', 'unknown')
            indicators = pattern_json.get('indicators', {})
            atr_h1 = indicators.get('atr', {}).get('H1')
            
            print("✅ VOLATILITY CHECK:")
            print(f"   Current volatility: {volatility}")
            print(f"   ATR H1 value: {atr_h1}")
            
            if atr_h1:
                if atr_h1 > 5.0 and volatility == 'high_price':
                    print(f"   ✅ Volatility assessment CORRECT (ATR {atr_h1} > 5.0 = high_price)")
                elif atr_h1 <= 5.0 and volatility in ['medium_price', 'low_price']:
                    print(f"   ✅ Volatility assessment CORRECT (ATR {atr_h1} <= 5.0 = {volatility})")
                else:
                    print(f"   ⚠️  Volatility assessment MISMATCH (ATR {atr_h1} vs {volatility})")
            else:
                print("   ⚠️  ATR H1 value missing")
            
            # 2. Check session vs UTC hour rules
            session = pattern_json.get('session', 'unknown')
            snapshot_hour = snapshot_time.hour if hasattr(snapshot_time, 'hour') else None
            
            print("\n✅ SESSION CHECK:")
            print(f"   Current session: {session}")
            print(f"   Snapshot UTC hour: {snapshot_hour}")
            
            if snapshot_hour is not None:
                expected_session = "unknown"
                if 0 <= snapshot_hour < 7:
                    expected_session = "Sydney"
                elif 7 <= snapshot_hour < 15:
                    expected_session = "London"  
                elif 15 <= snapshot_hour < 22:
                    expected_session = "New York"
                else:
                    expected_session = "Sydney"
                    
                if session == expected_session:
                    print(f"   ✅ Session CORRECT (Hour {snapshot_hour} = {session})")
                else:
                    print(f"   ⚠️  Session MISMATCH (Hour {snapshot_hour} should be {expected_session}, got {session})")
            
            # 3. Check JSON structure and keys
            print("\n✅ JSON STRUCTURE CHECK:")
            required_keys = ['symbol', 'snapshot_time', 'context', 'indicators', 'session', 'volatility']
            missing_keys = [key for key in required_keys if key not in pattern_json]
            
            if not missing_keys:
                print(f"   ✅ All required keys present: {required_keys}")
            else:
                print(f"   ⚠️  Missing keys: {missing_keys}")
            
            # Check snake_case convention
            all_keys = set()
            def collect_keys(obj, prefix=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        full_key = f"{prefix}.{key}" if prefix else key
                        all_keys.add(full_key)
                        collect_keys(value, full_key)
                elif isinstance(obj, list) and obj:
                    collect_keys(obj[0], prefix)
            
            collect_keys(pattern_json)
            
            non_snake_case = [key for key in all_keys if '_' in key.split('.')[-1] and not key.split('.')[-1].islower()]
            if not non_snake_case:
                print("   ✅ All keys follow snake_case convention")
            else:
                print(f"   ⚠️  Non-snake_case keys found: {non_snake_case[:5]}...")
            
            # 4. Check outcome predictions
            outcome_1h = pattern_json.get('outcome_1h', {})
            max_gain = outcome_1h.get('max_gain_pct_1h')
            max_loss = outcome_1h.get('max_loss_pct_1h')
            
            print("\n✅ PREDICTION DATA CHECK:")
            print(f"   Max gain prediction: {max_gain}%")
            print(f"   Max loss prediction: {max_loss}%")
            
            if max_gain is not None and max_loss is not None:
                print("   ✅ Outcome predictions available")
            else:
                print("   ⚠️  Outcome predictions missing")
            
            # 5. Check candle data optimization
            context = pattern_json.get('context', {})
            total_candles = sum(len(context.get(tf, [])) for tf in context.keys())
            
            print("\n✅ DATA OPTIMIZATION CHECK:")
            print(f"   Total candles across all timeframes: {total_candles}")
            for tf, candles in context.items():
                print(f"   {tf}: {len(candles)} candles")
            
            if total_candles <= 200:
                print("   ✅ Data optimized (≤200 candles)")
            else:
                print(f"   ⚠️  High candle count (>{total_candles})")
            
            # 6. Display formatted JSON sample
            print("\n✅ FORMATTED PATTERN JSON SAMPLE:")
            print("=" * 60)
            print(row['pretty_json'][:1000] + "..." if len(row['pretty_json']) > 1000 else row['pretty_json'])
            
            print("=" * 60)
            log_success("Pattern JSON validation completed")
            
    except Exception as e:
        log_error(f"Pattern JSON validation failed: {e}")


if __name__ == "__main__":
    # Test database connection
    try:
        with get_cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()
            log_success(f"Database connection successful: {version[0] if version else 'Unknown version'}")
            
        # Test getting latest M1 time
        latest_time = get_latest_m1_time(SYMBOL)
        if latest_time:
            log_success(f"Latest M1 time for {SYMBOL}: {latest_time}")
        else:
            log_error(f"No M1 data found for {SYMBOL}")
            
    except Exception as e:
        log_error(f"Database test failed: {e}")
