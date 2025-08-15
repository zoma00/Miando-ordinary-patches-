#!/usr/bin/env python3

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("📊 Checking symbols needing max gain/loss calculations...")
    
    with get_cursor(dict_cursor=False) as cur:
        # Check which symbols have missing calculations
        cur.execute("""
            SELECT symbol, 
                   COUNT(*) as total_snapshots,
                   COUNT(max_gain_pct_1h) as calculated,
                   COUNT(*) - COUNT(max_gain_pct_1h) as missing
            FROM trading_snapshots 
            WHERE snapshot_time >= NOW() - INTERVAL '3 days'
            GROUP BY symbol
            ORDER BY total_snapshots DESC;
        """)
        
        rows = cur.fetchall()
        
        print("Symbol   | Total  | Calc   | Missing")
        print("-" * 35)
        
        symbols_needing_calc = []
        
        for row in rows:
            symbol, total, calculated, missing = row
            print(f"{symbol:<8} | {total:<6} | {calculated:<6} | {missing:<7}")
            
            if missing > 0:
                symbols_needing_calc.append(symbol)
        
        print(f"\nSymbols needing calculations: {symbols_needing_calc}")
        
        if symbols_needing_calc:
            print("\n💡 To calculate missing data for each symbol, run:")
            for symbol in symbols_needing_calc:
                print(f"   python max_gain_loss_calc.py --symbol {symbol} --mode historical")
        else:
            print("\n✅ All symbols have complete max gain/loss data!")
        
except Exception as e:
    print(f"Error: {e}")
