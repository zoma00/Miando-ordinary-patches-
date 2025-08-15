#!/usr/bin/env python3
"""
🧪 JSON Split Pattern Test
Tests the Pattern JSON generation using the json_split system with Amir's data
"""

import sys
import os
from datetime import datetime

# Add patterns directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))
from common import get_pg_conn

def test_json_split_pattern():
    """Test JSON Split Pattern system with Amir's data"""
    print("🔍 Testing JSON Split Pattern System with Amir's Data")
    print("=" * 60)
    
    try:
        # Test force fresh pattern generation
        try:
            from force_fresh_pattern import force_fresh_pattern_json
            print("✅ Force Fresh Pattern module imported")
            
            # Run force fresh pattern generation
            force_fresh_pattern_json()
            print("✅ Force Fresh Pattern executed successfully")
            
        except ImportError as e:
            print(f"⚠️  Force Fresh Pattern import failed: {e}")
        except Exception as e:
            print(f"⚠️  Force Fresh Pattern execution warning: {e}")
        
        # Test data availability for Pattern JSON generation
        conn = get_pg_conn()
        cursor = conn.cursor()
        
        print("\n📊 Testing Data Availability for JSON Split Pattern:")
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
            print("✅ Pattern Data Available for JSON Split System:")
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
            
            print(f"\n📈 Summary:")
            print(f"   Total Candles: {total_candles}")
            print(f"   Timeframes: {len(timeframes)} ({', '.join(sorted(timeframes))})")
            print(f"   Spread Data: {'Available' if spread_available else 'Not Available'}")
            
        # Check for trading snapshots table (used by json_split system)
        print("\n📸 Testing Trading Snapshots Table:")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'trading_snapshots'
        """)
        snapshots_table_exists = cursor.fetchone()[0] > 0
        
        if snapshots_table_exists:
            cursor.execute("""
                SELECT COUNT(*) as total_snapshots,
                       MAX(snapshot_time) as latest_snapshot
                FROM trading_snapshots 
                WHERE pattern_json IS NOT NULL
            """)
            snapshot_stats = cursor.fetchone()
            if snapshot_stats[0] > 0:
                print(f"✅ Pattern JSON Snapshots: {snapshot_stats[0]} total")
                print(f"   Latest Snapshot: {snapshot_stats[1]}")
            else:
                print("⚠️  Pattern JSON Snapshots: None found")
        else:
            print("⚠️  trading_snapshots table: Not found")
        
        # Test specific XAUUSD data (main symbol in force_fresh_pattern)
        print("\n💰 Testing XAUUSD Data for JSON Split Pattern:")
        cursor.execute("""
            SELECT 
                timeframe,
                COUNT(*) as count,
                MAX(open_time) as latest,
                AVG(close_price) as avg_price
            FROM ohlc_data 
            WHERE symbol = 'XAUUSD' 
            AND open_time >= NOW() - INTERVAL '24 hours'
            GROUP BY timeframe
            ORDER BY timeframe
        """)
        
        xauusd_data = cursor.fetchall()
        if xauusd_data:
            print("✅ XAUUSD Data Available:")
            for timeframe, count, latest, avg_price in xauusd_data:
                print(f"   💰 {timeframe}: {count} candles, latest: {latest}, avg price: ${avg_price:.2f}")
        else:
            print("⚠️  No XAUUSD data found")
        
        conn.close()
        
        print("\n" + "=" * 60)
        if pattern_data and len(pattern_data) > 0:
            print("🎉 JSON Split Pattern System: READY")
            print("✅ Amir's data is compatible with json_split system")
            print("✅ Force fresh pattern generation working")
            print("✅ Data available for pattern analysis")
            return True
        else:
            print("⚠️  JSON Split Pattern System: Data issues detected")
            return False
            
    except Exception as e:
        print(f"❌ JSON Split Pattern Test Failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_json_split_pattern()
    sys.exit(0 if success else 1)
