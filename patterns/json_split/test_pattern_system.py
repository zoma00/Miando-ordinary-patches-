#!/usr/bin/env python3
# Comprehensive Pattern JSON System Test

from common import get_cursor, SYMBOL
import json
from datetime import datetime, timezone

def test_database_schema():
    """Test if required tables and columns exist."""
    print("\n🔍 Testing database schema...")
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Check tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('ohlc_data', 'trading_snapshots')
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            
            for table in tables:
                print(f"✅ Table found: {table['table_name']}")
            
            # Check pattern_json column
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'trading_snapshots'
                AND column_name = 'pattern_json'
            """)
            pattern_column = cur.fetchone()
            
            if pattern_column:
                print(f"✅ pattern_json column exists ({pattern_column['data_type']})")
                return True
            else:
                print("⚠️  pattern_json column not found - schema update needed")
                return False
                
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def test_data_availability():
    """Test if we have OHLC data available."""
    print("\n📊 Testing data availability...")
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Check OHLC data
            cur.execute("SELECT COUNT(*) as count FROM ohlc_data WHERE symbol = %s", (SYMBOL,))
            result = cur.fetchone()
            ohlc_count = result['count'] if result else 0
            
            print(f"📈 OHLC records for {SYMBOL}: {ohlc_count}")
            
            if ohlc_count > 0:
                # Check timeframes
                cur.execute("""
                    SELECT timeframe, COUNT(*) as count 
                    FROM ohlc_data 
                    WHERE symbol = %s 
                    GROUP BY timeframe 
                    ORDER BY timeframe
                """, (SYMBOL,))
                
                timeframes = cur.fetchall()
                for tf in timeframes:
                    print(f"  - {tf['timeframe']}: {tf['count']} records")
                
                return True
            else:
                print("⚠️  No OHLC data found - need to create test data")
                return False
                
    except Exception as e:
        print(f"❌ Data availability test failed: {e}")
        return False

def test_pattern_json_import():
    """Test Pattern JSON module imports."""
    print("\n📦 Testing Pattern JSON imports...")
    
    try:
        import pattern_json_live
        print("✅ pattern_json_live imported")
        
        import pattern_json_history
        print("✅ pattern_json_history imported")
        
        # Test function availability
        from pattern_json_live import build_pattern_json, store_pattern_json
        print("✅ Pattern JSON functions available")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def create_minimal_test_data():
    """Create minimal test data for Pattern JSON testing."""
    print("\n🔧 Creating minimal test data...")
    
    try:
        with get_cursor() as cur:
            # Clean existing test data
            cur.execute("DELETE FROM ohlc_data WHERE symbol = %s", (SYMBOL,))
            cur.execute("DELETE FROM trading_snapshots WHERE symbol = %s", (SYMBOL,))
            
            # Create basic test data for M1 timeframe (minimum required)
            base_time = datetime(2025, 8, 8, 12, 0, tzinfo=timezone.utc)
            
            for i in range(70):  # Create 70 M1 candles (more than our 60 limit)
                from datetime import timedelta
                open_time = base_time - timedelta(minutes=i)
                base_price = 2350.0
                
                cur.execute("""
                    INSERT INTO ohlc_data (
                        symbol, timeframe, open_time,
                        open_price, high_price, low_price, close_price, volume,
                        rsi, ema, atr, bb_middle, bb_upper, bb_lower
                    ) VALUES (
                        %s, 'M1', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    SYMBOL, open_time,
                    base_price, base_price + 1, base_price - 1, base_price + 0.5, 1000,
                    50.0 + (i % 50), base_price + 0.5, 3.0, base_price, base_price + 5, base_price - 5
                ))
            
            print(f"✅ Created 70 M1 test records for {SYMBOL}")
            return True
            
    except Exception as e:
        print(f"❌ Test data creation failed: {e}")
        return False

def test_pattern_json_generation():
    """Test Pattern JSON generation."""
    print("\n🧪 Testing Pattern JSON generation...")
    
    try:
        from pattern_json_live import build_pattern_json
        
        # Try to build pattern JSON
        pattern_json = build_pattern_json(SYMBOL)
        
        if pattern_json:
            print("✅ Pattern JSON generated successfully")
            
            # Validate structure
            required_keys = ['symbol', 'snapshot_time', 'context', 'indicators', 'outcome_1h']
            for key in required_keys:
                if key in pattern_json:
                    print(f"✅ Contains: {key}")
                else:
                    print(f"❌ Missing: {key}")
            
            # Check context structure
            if 'context' in pattern_json:
                context = pattern_json['context']
                total_candles = 0
                for timeframe, candles in context.items():
                    candle_count = len(candles)
                    total_candles += candle_count
                    print(f"  - {timeframe}: {candle_count} candles")
                
                print(f"📊 Total candles: {total_candles}")
                
                # Test JSON serialization
                json_str = json.dumps(pattern_json)
                size_kb = len(json_str) / 1024
                print(f"📦 JSON size: {size_kb:.1f} KB")
                
                return True
            else:
                print("❌ No context in pattern JSON")
                return False
        else:
            print("❌ Pattern JSON generation returned None")
            return False
            
    except Exception as e:
        print(f"❌ Pattern JSON generation failed: {e}")
        return False

def test_schema_update():
    """Test applying schema update for pattern_json column."""
    print("\n🔄 Testing schema update...")
    
    try:
        with get_cursor() as cur:
            # Check if pattern_json column exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = 'trading_snapshots'
                AND column_name = 'pattern_json'
            """)
            
            if cur.fetchone():
                print("✅ pattern_json column already exists")
                return True
            else:
                print("📝 Adding pattern_json column...")
                
                # Add the column
                cur.execute("""
                    ALTER TABLE trading_snapshots 
                    ADD COLUMN IF NOT EXISTS pattern_json JSONB
                """)
                
                # Add index
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trading_snapshots_pattern_json 
                    ON trading_snapshots USING GIN (pattern_json)
                """)
                
                print("✅ pattern_json column added with GIN index")
                return True
                
    except Exception as e:
        print(f"❌ Schema update failed: {e}")
        return False

def run_comprehensive_test():
    """Run comprehensive Pattern JSON system test."""
    print("🧪 Pattern JSON System - Comprehensive Test")
    print("=" * 50)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Data Availability", test_data_availability),
        ("Pattern JSON Imports", test_pattern_json_import),
        ("Schema Update", test_schema_update),
        ("Create Test Data", create_minimal_test_data),
        ("Pattern JSON Generation", test_pattern_json_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Pattern JSON system is ready!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)
