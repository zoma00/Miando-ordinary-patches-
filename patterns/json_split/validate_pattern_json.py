#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pattern JSON Quality Validation Script
Comprehensive validation of Pattern JSON data against your checklist requirements.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common import log_info, get_cursor, safe_float

def validate_pattern_json_detailed(symbol: str = 'XAUUSD') -> None:
    """
    Detailed validation of Pattern JSON with NULL handling.
    """
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Get recent pattern JSON records
            cur.execute("""
                SELECT 
                    symbol,
                    snapshot_time,
                    pattern_json->>'volatility' as volatility_level,
                    pattern_json->'indicators'->'atr'->>'H1' as atr_h1_value,
                    pattern_json->>'session' as trading_session,
                    EXTRACT(hour FROM snapshot_time) as utc_hour,
                    pattern_json->'outcome_1h'->>'max_gain_pct_1h' as max_gain,
                    pattern_json->'outcome_1h'->>'max_loss_pct_1h' as max_loss,
                    jsonb_pretty(pattern_json->'indicators') as indicators_json
                FROM trading_snapshots
                WHERE symbol = %s AND pattern_json IS NOT NULL
                ORDER BY snapshot_time DESC
                LIMIT 5
            """, (symbol,))
            
            rows = cur.fetchall()
            if not rows:
                log_info(f"No pattern JSON found for {symbol}")
                return
            
            print(f"🔍 Pattern JSON Validation for {symbol}")
            print("=" * 80)
            
            for i, row in enumerate(rows, 1):
                print(f"\n📊 Record {i}: {row['snapshot_time']}")
                print("-" * 50)
                
                # 1. Volatility Check
                volatility = row['volatility_level']
                atr_h1 = row['atr_h1_value']
                
                print(f"🎯 VOLATILITY: {volatility}")
                if atr_h1:
                    atr_val = safe_float(atr_h1)
                    expected = "high_price" if atr_val > 5.0 else "medium/low_price"
                    status = "✅" if (atr_val > 5.0 and volatility == 'high_price') or (atr_val <= 5.0 and volatility != 'high_price') else "⚠️"
                    print(f"   ATR H1: {atr_val} → Expected: {expected} {status}")
                else:
                    print(f"   ⚠️  ATR H1: NULL (indicator missing)")
                
                # 2. Session Check
                session = row['trading_session']
                utc_hour = int(row['utc_hour']) if row['utc_hour'] else 0
                
                print(f"🕐 SESSION: {session} (UTC Hour: {utc_hour})")
                
                # Correct session mapping
                if 22 <= utc_hour or utc_hour < 7:
                    expected_session = "Sydney"
                elif 7 <= utc_hour < 15:
                    expected_session = "London"
                elif 15 <= utc_hour < 22:
                    expected_session = "New York"
                else:
                    expected_session = "Unknown"
                
                status = "✅" if session == expected_session else "⚠️"
                print(f"   Expected: {expected_session} {status}")
                
                # 3. Predictions Check
                max_gain = row['max_gain']
                max_loss = row['max_loss']
                
                print(f"📈 PREDICTIONS:")
                if max_gain and max_loss:
                    print(f"   Max Gain: {max_gain}% ✅")
                    print(f"   Max Loss: {max_loss}% ✅")
                else:
                    print(f"   ⚠️  Predictions missing (Gain: {max_gain}, Loss: {max_loss})")
                
                # 4. Indicators Status
                print(f"📊 INDICATORS:")
                if row['indicators_json'] and row['indicators_json'] != 'null':
                    print(f"   ✅ Indicators present")
                else:
                    print(f"   ⚠️  Indicators missing or empty")
                
    except Exception as e:
        print(f"❌ Validation failed: {e}")


def main():
    """Run comprehensive Pattern JSON validation."""
    print("🔍 Pattern JSON Quality Validation")
    print("=" * 60)
    
    # Test database connection first
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trading_snapshots WHERE pattern_json IS NOT NULL")
            result = cur.fetchone()
            count = result[0] if result else 0
            log_info(f"Found {count} pattern JSON records in database")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Run detailed validation
    validate_pattern_json_detailed('XAUUSD')
    
    print("\n" + "=" * 80)
    print("📋 VALIDATION CHECKLIST SUMMARY:")
    print("   🎯 Volatility assessment vs ATR rules")
    print("   🕐 Session timing vs UTC hour mapping") 
    print("   📈 Outcome predictions availability")
    print("   📊 Technical indicators status")
    print("   🔧 Data structure validation")
    print("=" * 80)

if __name__ == "__main__":
    main()
