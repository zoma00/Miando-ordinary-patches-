#!/usr/bin/env python3
"""
📊 Amir Integration Dashboard
Comprehensive dashboard for monitoring Amir's MT5 data integration
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List
import psycopg2
import psycopg2.extras

# Add patterns directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))
from common import get_pg_conn

def get_amir_integration_status():
    """Get comprehensive status of Amir integration"""
    print("🌉 Amir Integration Dashboard")
    print("=" * 60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    try:
        conn = get_pg_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # 1. Data Freshness Check
        print("\n📊 DATA FRESHNESS STATUS")
        print("-" * 30)
        
        symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
        for symbol in symbols:
            cursor.execute("""
                SELECT 
                    symbol,
                    open_time,
                    spread,
                    volume,
                    EXTRACT(EPOCH FROM (NOW() - open_time))/60 as minutes_old
                FROM ohlc_data 
                WHERE symbol = %s 
                ORDER BY open_time DESC 
                LIMIT 1
            """, (symbol,))
            
            result = cursor.fetchone()
            if result:
                minutes_old = float(result['minutes_old'])
                status_emoji = "✅" if minutes_old <= 5 else "⚠️" if minutes_old <= 10 else "❌"
                spread = float(result['spread'] or 0)
                volume = int(result['volume'] or 0)
                
                print(f"{status_emoji} {symbol:<8} | {minutes_old:5.1f}min old | Spread: {spread:8.5f} | Vol: {volume:>8}")
            else:
                print(f"❌ {symbol:<8} | No data found")
        
        # 2. Connection Health
        print("\n🔗 CONNECTION HEALTH")
        print("-" * 30)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT symbol) as active_symbols,
                MAX(open_time) as latest_data
            FROM ohlc_data 
            WHERE open_time >= NOW() - INTERVAL '1 hour'
        """)
        
        health = cursor.fetchone()
        health_status = "✅ Healthy" if health['active_symbols'] >= 4 else "⚠️ Degraded" if health['active_symbols'] >= 2 else "❌ Critical"
        
        print(f"Status: {health_status}")
        print(f"Records Last Hour: {health['total_records']}")
        print(f"Active Symbols: {health['active_symbols']}/5")
        print(f"Latest Data: {health['latest_data']}")
        
        # 3. Trading Session Analysis
        print("\n🌍 TRADING SESSION ANALYSIS")
        print("-" * 30)
        
        current_hour = datetime.now().hour
        if 22 <= current_hour or current_hour < 7:
            session = 'Sydney 🇦🇺'
        elif 8 <= current_hour < 17:
            session = 'London 🇬🇧'
        elif 13 <= current_hour < 22:
            session = 'New York 🇺🇸'
        else:
            session = 'Transition'
        
        print(f"Current Session: {session}")
        print(f"UTC Hour: {current_hour}:00")
        
        # Get session-based data volume
        cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM open_time) as hour,
                COUNT(*) as record_count
            FROM ohlc_data 
            WHERE open_time >= NOW() - INTERVAL '24 hours'
            GROUP BY EXTRACT(HOUR FROM open_time)
            ORDER BY hour
        """)
        
        hourly_data = cursor.fetchall()
        total_24h = sum(row['record_count'] for row in hourly_data)
        print(f"24h Data Points: {total_24h}")
        
        # 4. Pattern JSON Integration Status
        print("\n🔄 PATTERN JSON INTEGRATION")
        print("-" * 30)
        
        # Check if force-fresh system can use Amir's data
        cursor.execute("""
            SELECT 
                symbol,
                open_time,
                CASE 
                    WHEN EXTRACT(EPOCH FROM (NOW() - open_time))/60 <= 2 THEN 'Ready for Force-Fresh'
                    WHEN EXTRACT(EPOCH FROM (NOW() - open_time))/60 <= 5 THEN 'Usable'
                    ELSE 'Too Stale'
                END as pattern_json_status
            FROM ohlc_data o1
            WHERE o1.open_time = (
                SELECT MAX(o2.open_time) 
                FROM ohlc_data o2 
                WHERE o2.symbol = o1.symbol
            )
            ORDER BY symbol
        """)
        
        pattern_status = cursor.fetchall()
        for row in pattern_status:
            status_emoji = "🚀" if "Ready" in row['pattern_json_status'] else "✅" if "Usable" in row['pattern_json_status'] else "❌"
            print(f"{status_emoji} {row['symbol']:<8} | {row['pattern_json_status']}")
        
        # 5. Data Quality Metrics
        print("\n📈 DATA QUALITY METRICS")
        print("-" * 30)
        
        cursor.execute("""
            SELECT 
                symbol,
                COUNT(*) as records_today,
                AVG(spread) as avg_spread,
                MIN(spread) as min_spread,
                MAX(spread) as max_spread,
                SUM(volume) as total_volume
            FROM ohlc_data 
            WHERE open_time >= CURRENT_DATE
                AND spread > 0
            GROUP BY symbol
            ORDER BY symbol
        """)
        
        quality_metrics = cursor.fetchall()
        print(f"{'Symbol':<8} | {'Records':<8} | {'Avg Spread':<12} | {'Volume':<12}")
        print("-" * 50)
        
        for metric in quality_metrics:
            avg_spread = float(metric['avg_spread'] or 0)
            total_vol = int(metric['total_volume'] or 0)
            print(f"{metric['symbol']:<8} | {metric['records_today']:<8} | {avg_spread:>10.5f} | {total_vol:>10}")
        
        # 6. Integration Recommendations
        print("\n💡 INTEGRATION RECOMMENDATIONS")
        print("-" * 30)
        
        recommendations = []
        
        # Check data freshness
        fresh_symbols = 0
        for symbol in symbols:
            cursor.execute("""
                SELECT EXTRACT(EPOCH FROM (NOW() - MAX(open_time)))/60 as minutes_old
                FROM ohlc_data WHERE symbol = %s
            """, (symbol,))
            result = cursor.fetchone()
            if result and result['minutes_old'] is not None and result['minutes_old'] <= 5:
                fresh_symbols += 1
        
        if fresh_symbols >= 4:
            recommendations.append("✅ Data freshness is good - Pattern JSON can use force-fresh mode")
        elif fresh_symbols >= 2:
            recommendations.append("⚠️  Some symbols have stale data - Consider bridge script")
        else:
            recommendations.append("❌ Most data is stale - Check Amir's connection")
        
        # Check spread data
        cursor.execute("""
            SELECT COUNT(*) as symbols_with_spread
            FROM (
                SELECT symbol 
                FROM ohlc_data 
                WHERE open_time >= NOW() - INTERVAL '1 hour'
                    AND spread > 0
                GROUP BY symbol
            ) s
        """)
        
        symbols_with_spread = cursor.fetchone()['symbols_with_spread']
        
        if symbols_with_spread >= 4:
            recommendations.append("✅ Spread data available - Pattern JSON accuracy improved")
        else:
            recommendations.append("⚠️  Limited spread data - Ask Amir to enhance collection")
        
        # Print recommendations
        for rec in recommendations:
            print(f"  {rec}")
        
        # 7. Quick Actions
        print("\n🚀 QUICK ACTIONS")
        print("-" * 30)
        print("1. Test Pattern JSON with Amir's data:")
        print("   cd patterns/json_split && python3 pattern_json_live.py --force-fresh")
        print()
        print("2. Start data bridge:")
        print("   python3 data_bridge.py")
        print()
        print("3. Monitor data freshness:")
        print("   python3 monitor.py --check")
        print()
        print("4. Send enhancement spec to Amir:")
        print("   cat ENHANCEMENT_SPEC.md")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Dashboard error: {str(e)}")

def test_pattern_json_integration():
    """Test Pattern JSON integration with Amir's data"""
    print("\n🧪 TESTING PATTERN JSON INTEGRATION")
    print("=" * 50)
    
    try:
        # Import Pattern JSON functions
        sys.path.append(os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))
        from pattern_json_live import build_pattern_json
        from common import get_latest_m1_time
        
        symbol = 'XAUUSD'
        
        # Test regular mode
        print(f"📊 Testing Pattern JSON for {symbol}...")
        
        # Get latest M1 time from Amir's data
        latest_time = get_latest_m1_time(symbol, force_fresh=False)
        print(f"Latest M1 time (regular): {latest_time}")
        
        # Test force-fresh mode
        latest_time_fresh = get_latest_m1_time(symbol, force_fresh=True)
        print(f"Latest M1 time (force-fresh): {latest_time_fresh}")
        
        # Generate Pattern JSON
        pattern_json = build_pattern_json(symbol, force_fresh=True)
        
        if pattern_json:
            print("✅ Pattern JSON generated successfully!")
            print(f"📈 Pattern contains {len(pattern_json.get('candles', []))} candles")
            
            # Check spread data
            if 'spread' in pattern_json:
                print(f"💰 Current spread: {pattern_json['spread']}")
            
            # Check session
            if 'session' in pattern_json:
                print(f"🌍 Trading session: {pattern_json['session']}")
                
        else:
            print("❌ Pattern JSON generation failed")
        
    except Exception as e:
        print(f"❌ Pattern JSON test failed: {str(e)}")

def main():
    """Main dashboard execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Amir Integration Dashboard')
    parser.add_argument('--status', action='store_true', help='Show integration status', default=True)
    parser.add_argument('--test', action='store_true', help='Test Pattern JSON integration')
    
    args = parser.parse_args()
    
    if args.test:
        test_pattern_json_integration()
    else:
        get_amir_integration_status()

if __name__ == "__main__":
    main()
