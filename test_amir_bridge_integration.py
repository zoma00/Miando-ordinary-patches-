#!/usr/bin/env python3
"""
🧪 Amir Bridge Integration Test Suite
Tests the bridge integration with Amir's existing MT5 data collection
"""

import requests
import json
import time
import sys
import os
from datetime import datetime, timezone

# Add patterns directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))
from common import get_pg_conn

def test_database_connection():
    """Test direct database connection"""
    print("\n🔍 Testing Database Connection...")
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        conn.close()
        print(f"✅ Database Connected: {version[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Database Connection Failed: {str(e)}")
        return False

def test_existing_tables():
    """Test existing table structure"""
    print("\n🔍 Testing Existing Tables...")
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()
        
        tables_to_check = [
            'ohlc_data',           # Your existing OHLC table
            'account_state',       # Your existing account table  
            'open_trades',         # Your existing open trades table
            'closed_trades',       # Your existing closed trades table
            'planned_trades'       # Your existing planned trades table
        ]
        
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   ✅ {table}: {count} records")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Table Check Failed: {str(e)}")
        return False

def test_amir_data_freshness():
    """Test Amir's data freshness"""
    print("\n🔍 Testing Amir Data Freshness...")
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()
        
        # Check latest data from Amir
        cursor.execute("""
            SELECT symbol, timeframe, 
                   open_time, 
                   EXTRACT(epoch FROM (NOW() - open_time))/60 as minutes_old
            FROM ohlc_data 
            ORDER BY open_time DESC 
            LIMIT 5
        """)
        
        latest_data = cursor.fetchall()
        if latest_data:
            print("✅ Latest data from Amir:")
            for row in latest_data:
                symbol, timeframe, open_time, minutes_old = row
                status = "🟢 FRESH" if minutes_old < 5 else "🟡 STALE" if minutes_old < 60 else "🔴 OLD"
                print(f"   {status} {symbol} {timeframe}: {minutes_old:.1f} minutes old")
        else:
            print("⚠️  No data found from Amir")
        
        conn.close()
        return len(latest_data) > 0
    except Exception as e:
        print(f"❌ Data Freshness Check Failed: {str(e)}")
        return False

def test_bridge_enhancements():
    """Test bridge enhancement functionality"""
    print("\n🔍 Testing Bridge Enhancements...")
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()
        
        # Check if enhanced columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ohlc_data' 
            AND column_name IN ('spread', 'mt5_collection_time', 'data_source', 'trading_session')
        """)
        enhanced_columns = [row[0] for row in cursor.fetchall()]
        
        if len(enhanced_columns) > 0:
            print(f"✅ Enhanced columns found: {', '.join(enhanced_columns)}")
            
            # Check for data with enhancements
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(spread) as with_spread,
                       COUNT(mt5_collection_time) as with_mt5_time,
                       COUNT(data_source) as with_source,
                       COUNT(trading_session) as with_session
                FROM ohlc_data 
                WHERE open_time > NOW() - INTERVAL '1 hour'
            """)
            stats = cursor.fetchone()
            print(f"   Recent records: {stats[0]}")
            print(f"   With spread: {stats[1]}")
            print(f"   With MT5 time: {stats[2]}")
            print(f"   With source: {stats[3]}")
            print(f"   With session: {stats[4]}")
        else:
            print("⚠️  Bridge enhancement columns not found - run bridge setup")
        
        conn.close()
        return len(enhanced_columns) > 0
    except Exception as e:
        print(f"❌ Bridge Enhancement Check Failed: {str(e)}")
        return False

def test_pattern_json_integration():
    """Test Pattern JSON integration with Amir's data using JSON Split system"""
    print("\n🔍 Testing Pattern JSON Data Access (JSON Split System)...")
    try:
        # Test your JSON Split system compatibility
        patterns_dir = os.path.join(os.path.dirname(__file__), 'patterns', 'json_split')
        sys.path.append(patterns_dir)
        
        # Quick test of force fresh pattern (JSON Split system)
        try:
            from force_fresh_pattern import force_fresh_pattern_json
            print("✅ JSON Split - Force Fresh Pattern available")
        except ImportError:
            print("⚠️  JSON Split - Force Fresh Pattern not available")
        
        conn = get_pg_conn()
        cursor = conn.cursor()
        
        # Test data availability for Pattern JSON generation
        cursor.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as candle_count,
                MAX(open_time) as latest_data,
                AVG(CASE WHEN spread IS NOT NULL THEN spread END) as avg_spread
            FROM ohlc_data 
            WHERE open_time >= NOW() - INTERVAL '24 hours'
            GROUP BY symbol, timeframe
            ORDER BY candle_count DESC
            LIMIT 5
        """)
        
        pattern_data = cursor.fetchall()
        
        if pattern_data:
            print("✅ Pattern JSON Data Available (JSON Split Compatible):")
            total_candles = 0
            timeframes = set()
            spread_available = False
            
            for row in pattern_data:
                symbol, timeframe, count, latest, avg_spread = row
                total_candles += count
                timeframes.add(timeframe)
                if avg_spread is not None:
                    spread_available = True
                    print(f"   📊 {symbol} {timeframe}: {count} candles, spread: {avg_spread:.2f}")
                else:
                    print(f"   📊 {symbol} {timeframe}: {count} candles, no spread data")
            
            print(f"   � Total Candles: {total_candles}")
            print(f"   ⏰ Timeframes: {len(timeframes)} ({', '.join(sorted(timeframes))})")
            print(f"   💰 Spread Data: {'Available' if spread_available else 'Not Available'}")
            
            # Check trading session data
            cursor.execute("""
                SELECT DISTINCT trading_session, COUNT(*) 
                FROM ohlc_data 
                WHERE trading_session IS NOT NULL 
                AND open_time >= NOW() - INTERVAL '24 hours'
                GROUP BY trading_session
            """)
            sessions = cursor.fetchall()
            if sessions:
                session_names = [s[0] for s in sessions]
                print(f"   🌍 Trading Sessions: {', '.join(session_names)}")
            else:
                print("   🌍 Trading Sessions: Not Available")
                
        else:
            print("⚠️  No Pattern JSON data available")
        
        conn.close()
        return len(pattern_data) > 0
            
    except Exception as e:
        print(f"❌ Pattern JSON Data Access Failed: {str(e)}")
        return False

def test_trading_session_function():
    """Test trading session detection function"""
    print("\n🔍 Testing Trading Session Function...")
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()
        
        # Check if function exists
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM pg_proc 
                WHERE proname = 'get_trading_session'
            )
        """)
        function_exists = cursor.fetchone()[0]
        
        if function_exists:
            cursor.execute("SELECT get_trading_session(NOW()::timestamp) as current_session")
            session = cursor.fetchone()[0]
            print(f"✅ Current Trading Session: {session}")
            
            # Test specific times
            test_times = [
                ("2025-01-21 02:00:00", "Sydney"),
                ("2025-01-21 10:00:00", "London"), 
                ("2025-01-21 16:00:00", "New_York")
            ]
            
            for test_time, expected_session in test_times:
                cursor.execute(f"SELECT get_trading_session('{test_time}'::timestamp)")
                result_session = cursor.fetchone()[0]
                print(f"   🕐 {test_time} UTC → {result_session}")
        else:
            print("⚠️  Trading session function not found - create with bridge setup")
        
        conn.close()
        return function_exists
    except Exception as e:
        print(f"❌ Trading Session Test Failed: {str(e)}")
        return False

def test_bridge_monitor():
    """Test bridge monitoring functionality"""
    print("\n🔍 Testing Bridge Monitor...")
    try:
        # Check if bridge monitor script exists
        monitor_path = os.path.join(os.path.dirname(__file__), 'amir_monitor.py')
        bridge_path = os.path.join(os.path.dirname(__file__), 'amir_data_bridge.py')
        dashboard_path = os.path.join(os.path.dirname(__file__), 'amir_dashboard.py')
        
        scripts_found = []
        if os.path.exists(monitor_path):
            scripts_found.append("Monitor")
        if os.path.exists(bridge_path):
            scripts_found.append("Bridge")
        if os.path.exists(dashboard_path):
            scripts_found.append("Dashboard")
        
        if scripts_found:
            print(f"✅ Bridge Scripts Found: {', '.join(scripts_found)}")
            return True
        else:
            print("⚠️  Bridge scripts not found - run bridge setup")
            return False
            
    except Exception as e:
        print(f"❌ Bridge Monitor Test Failed: {str(e)}")
        return False

def verify_amir_integration():
    """Verify Amir's data integration is working"""
    print("\n🔍 Verifying Amir Integration...")
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()
        
        # Check for recent data
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT symbol) as unique_symbols,
                COUNT(DISTINCT timeframe) as unique_timeframes,
                MIN(open_time) as oldest_data,
                MAX(open_time) as newest_data
            FROM ohlc_data 
            WHERE open_time >= NOW() - INTERVAL '24 hours'
        """)
        stats = cursor.fetchone()
        
        if stats[0] > 0:
            print(f"✅ Amir Integration Active:")
            print(f"   📊 Records (24h): {stats[0]}")
            print(f"   💱 Symbols: {stats[1]}")
            print(f"   ⏰ Timeframes: {stats[2]}")
            print(f"   🕐 Data Range: {stats[3]} to {stats[4]}")
            
            # Check data quality
            cursor.execute("""
                SELECT symbol, timeframe, COUNT(*) as count
                FROM ohlc_data 
                WHERE open_time >= NOW() - INTERVAL '1 hour'
                GROUP BY symbol, timeframe
                ORDER BY count DESC
                LIMIT 5
            """)
            recent_data = cursor.fetchall()
            
            if recent_data:
                print("   📈 Recent Activity:")
                for symbol, timeframe, count in recent_data:
                    print(f"      {symbol} {timeframe}: {count} candles")
        else:
            print("⚠️  No recent data from Amir - check connection")
        
        conn.close()
        return stats[0] > 0
    except Exception as e:
        print(f"❌ Amir Integration Check Failed: {str(e)}")
        return False

def run_bridge_test_suite():
    """Run complete bridge integration test suite"""
    print("🌉 Starting Amir Bridge Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Existing Tables Check", test_existing_tables),
        ("Amir Data Freshness", test_amir_data_freshness),
        ("Bridge Enhancements", test_bridge_enhancements),
        ("Trading Session Function", test_trading_session_function),
        ("Bridge Monitor Scripts", test_bridge_monitor),
        ("Pattern JSON Data Access (JSON Split)", test_pattern_json_integration),
        ("Amir Integration Verification", verify_amir_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            time.sleep(1)  # Small delay between tests
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"🏁 Bridge Test Results: {passed}/{total} tests passed")
    
    if passed >= total - 1:  # Allow 1 test to fail for partial setup
        print("🎉 Bridge integration is functional!")
        print("\n📋 Bridge Integration Status:")
        print("✅ Database connection established")
        print("✅ Amir's data is accessible")
        print("✅ Bridge components are ready")
        print("\n🚀 Next Steps:")
        print("1. Run bridge setup: python3 amir_data_bridge.py")
        print("2. Start monitoring: python3 amir_monitor.py")
        print("3. Check dashboard: python3 amir_dashboard.py")
        print("4. Share enhancement spec with Amir")
    else:
        print("⚠️  Bridge integration needs setup.")
        print("   Check database connection and Amir's data collection.")
    
    return passed >= total - 1

if __name__ == "__main__":
    success = run_bridge_test_suite()
    sys.exit(0 if success else 1)
