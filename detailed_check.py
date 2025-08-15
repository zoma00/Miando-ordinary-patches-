#!/usr/bin/env python3

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("🔍 Detailed Trading Snapshots Analysis")
    print("="*60)
    
    # 1. Check table structure
    print("\n📋 Table Structure for max gain/loss columns:")
    print("-" * 50)
    with get_cursor(dict_cursor=True) as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'trading_snapshots' 
            AND column_name LIKE '%max_%'
            ORDER BY column_name;
        """)
        
        columns = cur.fetchall()
        for col in columns:
            print(f"  {col['column_name']:<20} | {col['data_type']:<15} | Nullable: {col['is_nullable']}")
    
    # 2. Check overall statistics
    print("\n📊 Overall Statistics:")
    print("-" * 30)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(max_gain_pct_1h) as gain_calculated,
                COUNT(max_loss_pct_1h) as loss_calculated,
                COUNT(*) - COUNT(max_gain_pct_1h) as gain_null,
                COUNT(*) - COUNT(max_loss_pct_1h) as loss_null
            FROM trading_snapshots;
        """)
        
        stats = cur.fetchone()
        total, gain_calc, loss_calc, gain_null, loss_null = stats
        
        print(f"  Total records: {total}")
        print(f"  max_gain_pct_1h calculated: {gain_calc} ({gain_calc/total*100:.1f}%)")
        print(f"  max_loss_pct_1h calculated: {loss_calc} ({loss_calc/total*100:.1f}%)")
        print(f"  max_gain_pct_1h NULL: {gain_null}")
        print(f"  max_loss_pct_1h NULL: {loss_null}")
    
    # 3. Check by symbol
    print("\n📈 Statistics by Symbol:")
    print("-" * 60)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as total,
                COUNT(max_gain_pct_1h) as gain_calc,
                COUNT(max_loss_pct_1h) as loss_calc,
                COUNT(*) - COUNT(max_gain_pct_1h) as gain_null,
                COUNT(*) - COUNT(max_loss_pct_1h) as loss_null
            FROM trading_snapshots 
            GROUP BY symbol
            ORDER BY symbol;
        """)
        
        symbol_stats = cur.fetchall()
        print("Symbol   | Total  | Gain Calc | Loss Calc | Gain NULL | Loss NULL")
        print("-" * 60)
        
        for row in symbol_stats:
            symbol, total, gain_calc, loss_calc, gain_null, loss_null = row
            print(f"{symbol:<8} | {total:<6} | {gain_calc:<9} | {loss_calc:<9} | {gain_null:<9} | {loss_null}")
    
    # 4. Show some NULL records if they exist
    print("\n🔍 Sample Records with NULL values:")
    print("-" * 70)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT symbol, snapshot_time, max_gain_pct_1h, max_loss_pct_1h
            FROM trading_snapshots 
            WHERE max_gain_pct_1h IS NULL OR max_loss_pct_1h IS NULL
            ORDER BY snapshot_time DESC
            LIMIT 10;
        """)
        
        null_records = cur.fetchall()
        
        if null_records:
            print("Symbol   | Timestamp            | Max Gain     | Max Loss")
            print("-" * 70)
            for row in null_records:
                symbol, timestamp, gain, loss = row
                # Handle timestamp
                if hasattr(timestamp, 'strftime'):
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                else:
                    time_str = str(timestamp)[:16]
                
                gain_str = f"{gain:.6f}" if gain is not None else "NULL"
                loss_str = f"{loss:.6f}" if loss is not None else "NULL"
                print(f"{symbol:<8} | {time_str:<20} | {gain_str:<12} | {loss_str}")
        else:
            print("✅ No NULL records found!")
    
    # 5. Show some calculated records
    print("\n✅ Sample Records with Calculated values:")
    print("-" * 70)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT symbol, snapshot_time, max_gain_pct_1h, max_loss_pct_1h
            FROM trading_snapshots 
            WHERE max_gain_pct_1h IS NOT NULL AND max_loss_pct_1h IS NOT NULL
            ORDER BY snapshot_time DESC
            LIMIT 10;
        """)
        
        calc_records = cur.fetchall()
        
        if calc_records:
            print("Symbol   | Timestamp            | Max Gain     | Max Loss")
            print("-" * 70)
            for row in calc_records:
                symbol, timestamp, gain, loss = row
                # Handle timestamp
                if hasattr(timestamp, 'strftime'):
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                else:
                    time_str = str(timestamp)[:16]
                
                gain_str = f"{gain:.6f}" if gain is not None else "NULL"
                loss_str = f"{loss:.6f}" if loss is not None else "NULL"
                print(f"{symbol:<8} | {time_str:<20} | {gain_str:<12} | {loss_str}")
        else:
            print("❌ No calculated records found!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
