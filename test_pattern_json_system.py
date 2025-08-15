#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database Connection Test and Pattern JSON Validation
Tests database connectivity and Pattern JSON functionality before deployment.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Test both local and Docker database configurations
TEST_DB_CONFIGS = [
    {
        "name": "Docker Database (port 5434)",
        "host": "localhost",
        "port": "5434",
        "database": "miando",
        "user": "miando",
        "password": "changeme"
    },
    {
        "name": "Local Database (port 5432)",
        "host": "localhost", 
        "port": "5432",
        "database": "miando",
        "user": "miando",
        "password": "changeme"
    },
    {
        "name": "Container Database (miando-db)",
        "host": "miando-db",
        "port": "5432", 
        "database": "miando",
        "user": "miando",
        "password": "changeme"
    }
]

def test_database_connection(db_config: Dict[str, str]) -> bool:
    """Test database connection with given configuration."""
    try:
        import psycopg2
        import psycopg2.extras
        
        print(f"🔌 Testing {db_config['name']}...")
        
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Test basic connection
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print(f"✅ Connection successful: {version['version'][:50]}...")
            
            # Check if our tables exist
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('ohlc_data', 'trading_snapshots')
                ORDER BY table_name
            """)
            
            tables = cur.fetchall()
            if tables:
                print(f"✅ Found tables: {[t['table_name'] for t in tables]}")
            else:
                print("⚠️  Required tables not found (ohlc_data, trading_snapshots)")
            
            # Check if pattern_json column exists
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'trading_snapshots'
                AND column_name = 'pattern_json'
            """)
            
            pattern_column = cur.fetchone()
            if pattern_column:
                print(f"✅ pattern_json column exists ({pattern_column['data_type']})")
            else:
                print("⚠️  pattern_json column not found - schema update needed")
            
            # Check data availability
            cur.execute("SELECT COUNT(*) as count FROM ohlc_data LIMIT 1")
            ohlc_count = cur.fetchone()
            print(f"📊 OHLC data records: {ohlc_count['count'] if ohlc_count else 0}")
            
            conn.close()
            return True
            
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def setup_test_environment():
    """Set up environment for testing."""
    print("🚀 Setting up test environment...")
    
    # Set environment variables for testing
    test_env = {
        "DB_HOST": "localhost",
        "DB_PORT": "5434",  # Docker port
        "DB_NAME": "miando",
        "DB_USER": "miando", 
        "DB_PASSWORD": "changeme",
        "SYMBOL": "XAUUSD"
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
        print(f"✅ Set {key}={value}")
    
    return test_env

def test_pattern_json_import():
    """Test importing Pattern JSON modules."""
    print("📦 Testing Pattern JSON module imports...")
    
    try:
        # Test pattern_json_live import
        sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')
        
        import pattern_json_live
        print("✅ pattern_json_live imported successfully")
        
        import pattern_json_history  
        print("✅ pattern_json_history imported successfully")
        
        import common
        print("✅ common module imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected import error: {e}")
        return False

def test_pattern_json_functions():
    """Test Pattern JSON function availability."""
    print("🔧 Testing Pattern JSON functions...")
    
    try:
        from pattern_json_live import build_pattern_json, store_pattern_json
        from pattern_json_history import build_historical_pattern_json
        from common import get_cursor, SYMBOL
        
        print("✅ All Pattern JSON functions available")
        
        # Test function signatures
        import inspect
        
        build_sig = inspect.signature(build_pattern_json)
        print(f"✅ build_pattern_json signature: {build_sig}")
        
        store_sig = inspect.signature(store_pattern_json)
        print(f"✅ store_pattern_json signature: {store_sig}")
        
        return True
        
    except Exception as e:
        print(f"❌ Function test failed: {e}")
        return False

def create_test_data():
    """Create minimal test data for Pattern JSON testing."""
    print("📊 Creating test data...")
    
    try:
        from common import get_cursor, SYMBOL
        
        with get_cursor() as cur:
            # Clean existing test data
            cur.execute("DELETE FROM ohlc_data WHERE symbol = %s", (SYMBOL,))
            cur.execute("DELETE FROM trading_snapshots WHERE symbol = %s", (SYMBOL,))
            
            # Create test data for multiple timeframes
            base_time = datetime(2025, 8, 8, 10, 0, tzinfo=timezone.utc)
            timeframes = ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']
            
            for tf_idx, timeframe in enumerate(timeframes):
                for i in range(100):  # Create enough data
                    if timeframe == 'M1':
                        time_offset = timedelta(minutes=i)
                    elif timeframe == 'M5':
                        time_offset = timedelta(minutes=i * 5)
                    elif timeframe == 'M15':
                        time_offset = timedelta(minutes=i * 15)
                    elif timeframe == 'H1':
                        time_offset = timedelta(hours=i)
                    elif timeframe == 'H4':
                        time_offset = timedelta(hours=i * 4)
                    else:  # D1
                        time_offset = timedelta(days=i)
                    
                    open_time = base_time - time_offset
                    base_price = 2350.0 + tf_idx
                    
                    cur.execute("""
                        INSERT INTO ohlc_data (
                            symbol, timeframe, open_time,
                            open_price, high_price, low_price, close_price, volume,
                            rsi, ema, atr, bb_middle, bb_upper, bb_lower,
                            adx, cci, macd, macd_signal, macd_hist, obv, sma,
                            stochastic_k, stochastic_d, willr
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        SYMBOL, timeframe, open_time,
                        base_price, base_price + 2, base_price - 1, base_price + 1, 1000,
                        50.0 + i, base_price + 1, 3.0, base_price, base_price + 5, base_price - 5,
                        30.0, 0.0, 0.1, 0.05, 0.05, 1000000, base_price,
                        50.0, 40.0, -50.0
                    ))
            
            print(f"✅ Created test data for {SYMBOL} across all timeframes")
            return True
            
    except Exception as e:
        print(f"❌ Test data creation failed: {e}")
        return False

def test_pattern_json_generation():
    """Test actual Pattern JSON generation."""
    print("🧪 Testing Pattern JSON generation...")
    
    try:
        from pattern_json_live import build_pattern_json
        from common import SYMBOL
        
        # Build pattern JSON
        pattern_json = build_pattern_json(SYMBOL)
        
        if pattern_json:
            print("✅ Pattern JSON generated successfully")
            
            # Validate structure
            required_keys = ['symbol', 'snapshot_time', 'context', 'indicators', 'outcome_1h']
            for key in required_keys:
                if key in pattern_json:
                    print(f"✅ Contains required key: {key}")
                else:
                    print(f"❌ Missing required key: {key}")
                    return False
            
            # Check context structure
            context = pattern_json['context']
            expected_timeframes = ['D1', 'H4', 'H1', 'M15', 'M5', 'M1']
            for tf in expected_timeframes:
                if tf in context:
                    candle_count = len(context[tf])
                    print(f"✅ {tf}: {candle_count} candles")
                else:
                    print(f"❌ Missing timeframe: {tf}")
            
            # Check size efficiency
            json_str = json.dumps(pattern_json)
            size_bytes = len(json_str)
            print(f"📊 Pattern JSON size: {size_bytes} bytes")
            
            total_candles = sum(len(candles) for candles in context.values())
            print(f"📊 Total candles: {total_candles}")
            
            if total_candles <= 152:
                print("✅ Size optimization target achieved (≤152 candles)")
            else:
                print(f"⚠️  Size optimization needs adjustment ({total_candles} > 152)")
            
            return True
        else:
            print("❌ Pattern JSON generation returned None")
            return False
            
    except Exception as e:
        print(f"❌ Pattern JSON generation failed: {e}")
        return False

def test_pattern_json_storage():
    """Test Pattern JSON database storage."""
    print("💾 Testing Pattern JSON storage...")
    
    try:
        from pattern_json_live import build_pattern_json, store_pattern_json
        from common import SYMBOL, get_cursor
        
        # Generate pattern JSON
        pattern_json = build_pattern_json(SYMBOL)
        if not pattern_json:
            print("❌ Cannot test storage - pattern generation failed")
            return False
        
        # Store in database
        snapshot_time = datetime.fromisoformat(pattern_json["snapshot_time"].replace('Z', '+00:00'))
        success = store_pattern_json(SYMBOL, snapshot_time, pattern_json)
        
        if success:
            print("✅ Pattern JSON stored successfully")
            
            # Verify in database
            with get_cursor(dict_cursor=True) as cur:
                cur.execute("""
                    SELECT pattern_json, created_at
                    FROM trading_snapshots
                    WHERE symbol = %s AND snapshot_time = %s
                """, (SYMBOL, snapshot_time))
                
                row = cur.fetchone()
                if row:
                    stored_json = row['pattern_json']
                    print(f"✅ Verified storage - record created at {row['created_at']}")
                    
                    # Validate stored structure
                    if stored_json['symbol'] == SYMBOL:
                        print("✅ Stored data integrity verified")
                        return True
                    else:
                        print("❌ Stored data integrity check failed")
                        return False
                else:
                    print("❌ Stored record not found")
                    return False
        else:
            print("❌ Pattern JSON storage failed")
            return False
            
    except Exception as e:
        print(f"❌ Pattern JSON storage test failed: {e}")
        return False

def run_comprehensive_test():
    """Run comprehensive Pattern JSON system test."""
    print("🧪 Pattern JSON System - Comprehensive Test")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Database Connection
    print("\n1️⃣ Database Connection Test")
    db_connected = False
    for db_config in TEST_DB_CONFIGS:
        if test_database_connection(db_config):
            db_connected = True
            break
    
    test_results.append(("Database Connection", db_connected))
    
    if not db_connected:
        print("❌ Cannot proceed without database connection")
        return False
    
    # Test 2: Environment Setup
    print("\n2️⃣ Environment Setup")
    env_setup = setup_test_environment()
    test_results.append(("Environment Setup", bool(env_setup)))
    
    # Test 3: Module Imports
    print("\n3️⃣ Module Import Test")
    imports_ok = test_pattern_json_import()
    test_results.append(("Module Imports", imports_ok))
    
    if not imports_ok:
        print("❌ Cannot proceed without module imports")
        return False
    
    # Test 4: Function Availability
    print("\n4️⃣ Function Availability Test")
    functions_ok = test_pattern_json_functions()
    test_results.append(("Function Availability", functions_ok))
    
    # Test 5: Test Data Creation
    print("\n5️⃣ Test Data Creation")
    test_data_ok = create_test_data()
    test_results.append(("Test Data Creation", test_data_ok))
    
    if not test_data_ok:
        print("❌ Cannot proceed without test data")
        return False
    
    # Test 6: Pattern JSON Generation
    print("\n6️⃣ Pattern JSON Generation Test")
    generation_ok = test_pattern_json_generation()
    test_results.append(("Pattern JSON Generation", generation_ok))
    
    # Test 7: Pattern JSON Storage
    print("\n7️⃣ Pattern JSON Storage Test")
    storage_ok = test_pattern_json_storage()
    test_results.append(("Pattern JSON Storage", storage_ok))
    
    # Results Summary
    print("\n" + "=" * 60)
    print("🎯 Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Pattern JSON System Ready for Deployment!")
        print("\n📋 Next Steps:")
        print("1. Run deployment script: ./deploy_pattern_json.sh")
        print("2. Start live exports: python3 pattern_json_live.py")
        print("3. Monitor system performance")
    else:
        print("⚠️  Some tests failed - Please resolve issues before deployment")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        exit(1)
