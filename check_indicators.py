#!/usr/bin/env python3
"""
Check technical indicators in the ohlc_data table to see what's working and available.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("📊 Technical Indicators Analysis - OHLC Data Table")
    print("="*65)
    
    # 1. Check table structure for indicators
    print("\n📋 Available Technical Indicators:")
    print("-" * 50)
    with get_cursor(dict_cursor=True) as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'ohlc_data' 
            AND column_name NOT IN ('id', 'symbol', 'timeframe', 'open_time', 'open_price', 
                                   'high_price', 'low_price', 'close_price', 'volume', 
                                   'mt5_collection_time', 'data_source', 'trading_session', 'spread')
            ORDER BY column_name;
        """)
        
        indicators = cur.fetchall()
        
        print("Indicator        | Data Type        | Nullable")
        print("-" * 50)
        for ind in indicators:
            print(f"{ind['column_name']:<16} | {ind['data_type']:<16} | {ind['is_nullable']}")
    
    # 2. Check overall indicator coverage
    print("\n📊 Indicator Coverage Statistics:")
    print("-" * 60)
    with get_cursor(dict_cursor=False) as cur:
        indicator_columns = [
            'adx', 'atr', 'bb_middle', 'bb_upper', 'bb_lower', 'cci', 
            'ema', 'macd', 'macd_signal', 'macd_hist', 'obv', 'rsi', 
            'sma', 'stochastic_k', 'stochastic_d', 'willr'
        ]
        
        for indicator in indicator_columns:
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT({indicator}) as calculated,
                    COUNT(*) - COUNT({indicator}) as null_count,
                    ROUND(COUNT({indicator}) * 100.0 / COUNT(*), 1) as coverage_pct
                FROM ohlc_data;
            """)
            
            stats = cur.fetchone()
            total, calculated, null_count, coverage = stats
            
            status = "✅" if coverage >= 95 else "⚠️" if coverage >= 70 else "❌"
            print(f"{indicator:<15} | {total:>8} | {calculated:>8} | {null_count:>8} | {coverage:>6.1f}% {status}")
    
    print("\nColumns: Total | Calculated | NULL | Coverage")
    
    # 3. Check coverage by symbol and timeframe
    print("\n📈 Coverage by Symbol and Timeframe:")
    print("-" * 70)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as total_records,
                COUNT(rsi) as rsi_count,
                COUNT(macd) as macd_count,
                COUNT(adx) as adx_count,
                COUNT(bb_middle) as bb_count,
                ROUND(COUNT(rsi) * 100.0 / COUNT(*), 1) as rsi_coverage
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe;
        """)
        
        coverage_data = cur.fetchall()
        
        print("Symbol   | TF | Total  | RSI  | MACD | ADX  | BB   | RSI Coverage")
        print("-" * 70)
        
        for row in coverage_data:
            symbol, tf, total, rsi, macd, adx, bb, rsi_cov = row
            status = "✅" if rsi_cov >= 95 else "⚠️" if rsi_cov >= 70 else "❌"
            print(f"{symbol:<8} | {tf:<2} | {total:>6} | {rsi:>4} | {macd:>4} | {adx:>4} | {bb:>4} | {rsi_cov:>6.1f}% {status}")
    
    # 4. Show recent records with indicators
    print("\n🔍 Recent Records with Indicators (latest first):")
    print("-" * 100)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol, timeframe, open_time, close_price,
                ROUND(rsi::numeric, 2) as rsi,
                ROUND(macd::numeric, 4) as macd,
                ROUND(adx::numeric, 2) as adx,
                ROUND(atr::numeric, 5) as atr,
                ROUND(bb_middle::numeric, 5) as bb_mid
            FROM ohlc_data 
            WHERE rsi IS NOT NULL 
            ORDER BY open_time DESC 
            LIMIT 15;
        """)
        
        recent_data = cur.fetchall()
        
        if recent_data:
            print("Symbol   | TF | Time             | Close   | RSI   | MACD    | ADX   | ATR     | BB_Mid")
            print("-" * 100)
            for row in recent_data:
                symbol, tf, open_time, close, rsi, macd, adx, atr, bb_mid = row
                time_str = open_time.strftime("%Y-%m-%d %H:%M")
                
                # Handle None values
                rsi_str = f"{rsi:>5.1f}" if rsi is not None else "  N/A"
                macd_str = f"{macd:>7.4f}" if macd is not None else "   N/A"
                adx_str = f"{adx:>5.1f}" if adx is not None else "  N/A"
                atr_str = f"{atr:>7.5f}" if atr is not None else "   N/A"
                bb_str = f"{bb_mid:>7.5f}" if bb_mid is not None else "   N/A"
                
                print(f"{symbol:<8} | {tf:<2} | {time_str} | {close:>7.5f} | {rsi_str} | {macd_str} | {adx_str} | {atr_str} | {bb_str}")
        else:
            print("❌ No records with indicators found!")
    
    # 5. Check for data gaps in indicators
    print("\n🔍 Recent Records WITHOUT Indicators (potential issues):")
    print("-" * 80)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol, timeframe, open_time, close_price
            FROM ohlc_data 
            WHERE rsi IS NULL OR macd IS NULL
            ORDER BY open_time DESC 
            LIMIT 10;
        """)
        
        gap_data = cur.fetchall()
        
        if gap_data:
            print("Symbol   | TF | Time             | Close   | Issue")
            print("-" * 80)
            for row in gap_data:
                symbol, tf, open_time, close = row
                time_str = open_time.strftime("%Y-%m-%d %H:%M")
                print(f"{symbol:<8} | {tf:<2} | {time_str} | {close:>7.5f} | Missing indicators")
        else:
            print("✅ No recent records missing indicators!")
    
    # 6. Show indicator value ranges
    print("\n📊 Indicator Value Ranges (for validation):")
    print("-" * 80)
    with get_cursor(dict_cursor=False) as cur:
        indicators_to_check = ['rsi', 'adx', 'atr', 'cci']
        
        for indicator in indicators_to_check:
            cur.execute(f"""
                SELECT 
                    MIN({indicator}) as min_val,
                    MAX({indicator}) as max_val,
                    AVG({indicator}) as avg_val,
                    COUNT({indicator}) as count
                FROM ohlc_data 
                WHERE {indicator} IS NOT NULL;
            """)
            
            stats = cur.fetchone()
            if stats and stats[3] > 0:  # count > 0
                min_val, max_val, avg_val, count = stats
                print(f"{indicator.upper():<12} | Min: {min_val:>8.2f} | Max: {max_val:>8.2f} | Avg: {avg_val:>8.2f} | Count: {count:>6}")
    
    # 7. Check latest calculation time
    print("\n⏰ Latest Indicator Calculation Times:")
    print("-" * 50)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                MAX(open_time) as latest_with_indicators
            FROM ohlc_data 
            WHERE rsi IS NOT NULL
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe;
        """)
        
        latest_data = cur.fetchall()
        
        for row in latest_data:
            symbol, tf, latest_time = row
            time_str = latest_time.strftime("%Y-%m-%d %H:%M")
            print(f"{symbol} {tf}: Latest indicators at {time_str}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
