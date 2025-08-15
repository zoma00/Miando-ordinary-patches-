#!/usr/bin/env python3
"""
Check database schema and max gain/loss data in trading snapshots.
"""

import sys
import os

# Add the patterns directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
patterns_dir = os.path.join(current_dir, 'patterns', 'json_split')
sys.path.insert(0, patterns_dir)

from common import get_cursor, log_info, log_error, log_success

def check_database_schema():
    """Check if max gain/loss columns exist in trading_snapshots table."""
    
    try:
        log_info("Checking database schema for max gain/loss columns...")
        
        with get_cursor() as cur:
            # Check for gain/loss columns
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'trading_snapshots'
                AND (column_name LIKE '%gain%' OR column_name LIKE '%loss%')
                ORDER BY column_name;
            """)
            
            gain_loss_cols = cur.fetchall()
            
            print("\n" + "="*60)
            print("DATABASE SCHEMA ANALYSIS")
            print("="*60)
            
            if gain_loss_cols:
                print("📊 Max Gain/Loss columns found:")
                for row in gain_loss_cols:
                    if hasattr(row, 'keys'):
                        col_name = row['column_name']
                        data_type = row['data_type']
                        nullable = row['is_nullable']
                    else:
                        col_name, data_type, nullable = row
                    print(f"  ✅ {col_name}: {data_type} (nullable: {nullable})")
            else:
                print("❌ No max gain/loss columns found!")
                
                # Show all columns in trading_snapshots
                print("\n📋 All columns in trading_snapshots:")
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_name = 'trading_snapshots'
                    ORDER BY ordinal_position;
                """)
                
                all_cols = cur.fetchall()
                for row in all_cols:
                    if hasattr(row, 'keys'):
                        print(f"  - {row['column_name']}: {row['data_type']}")
                    else:
                        print(f"  - {row[0]}: {row[1]}")
            
            return len(gain_loss_cols) > 0
            
    except Exception as e:
        log_error(f"Error checking database schema: {e}")
        return False

def calculate_max_gain_loss_manually():
    """Calculate max gain/loss percentages manually from OHLC data."""
    
    try:
        log_info("Calculating max gain/loss percentages manually from recent H1 data...")
        
        with get_cursor() as cur:
            # Get recent OHLC data for H1 timeframe
            cur.execute("""
                SELECT 
                    symbol,
                    open_time,
                    open_price,
                    high_price,
                    low_price,
                    close_price
                FROM ohlc_data 
                WHERE timeframe = 'H1'
                AND symbol = 'XAUUSD'
                AND open_time >= NOW() - INTERVAL '24 hours'
                ORDER BY open_time DESC
                LIMIT 24;
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("❌ No H1 OHLC data found for the last 24 hours")
                return
            
            print("\n" + "="*80)
            print("MANUAL MAX GAIN/LOSS CALCULATION (H1 TIMEFRAME)")
            print("="*80)
            print(f"{'Time':<20} | {'Open':<8} | {'High':<8} | {'Low':<8} | {'Close':<8} | {'Max Gain %':<12} | {'Max Loss %':<12}")
            print("-" * 80)
            
            for row in rows:
                if hasattr(row, 'keys'):
                    symbol = row['symbol']
                    open_time = row['open_time']
                    open_price = float(row['open_price']) if row['open_price'] else 0
                    high_price = float(row['high_price']) if row['high_price'] else 0
                    low_price = float(row['low_price']) if row['low_price'] else 0
                    close_price = float(row['close_price']) if row['close_price'] else 0
                else:
                    symbol, open_time, open_price, high_price, low_price, close_price = row
                    open_price = float(open_price) if open_price else 0
                    high_price = float(high_price) if high_price else 0
                    low_price = float(low_price) if low_price else 0
                    close_price = float(close_price) if close_price else 0
                
                if open_price > 0:
                    # Calculate max gain and loss percentages relative to open price
                    max_gain_pct = ((high_price - open_price) / open_price) * 100
                    max_loss_pct = ((low_price - open_price) / open_price) * 100
                    
                    time_str = open_time.strftime("%Y-%m-%d %H:%M")
                    print(f"{time_str:<20} | {open_price:8.5f} | {high_price:8.5f} | {low_price:8.5f} | {close_price:8.5f} | {max_gain_pct:+8.4f}%    | {max_loss_pct:+8.4f}%")
                else:
                    time_str = open_time.strftime("%Y-%m-%d %H:%M")
                    print(f"{time_str:<20} | Invalid price data")
            
            print("-" * 80)
            log_success("Manual calculation completed")
            
    except Exception as e:
        log_error(f"Error calculating max gain/loss manually: {e}")

def main():
    """Main function to check schema and calculate max gain/loss."""
    
    print("🔍 MAX GAIN/LOSS ANALYSIS TOOL")
    print("="*50)
    
    # Check if the max gain/loss columns exist
    has_columns = check_database_schema()
    
    if has_columns:
        log_success("Max gain/loss columns found in database!")
        # Could run the existing max_gain_loss_calc.py script here
        print("\n💡 You can run the max gain/loss calculator:")
        print("   cd patterns/json_split && python max_gain_loss_calc.py")
    else:
        log_info("Max gain/loss columns not found. Creating manual calculation...")
        calculate_max_gain_loss_manually()
        
        print("\n💡 To add max gain/loss columns to the database:")
        print("   1. Check if there's an SQL migration script")
        print("   2. Or run the max_gain_loss_calc.py script to add the columns")

if __name__ == "__main__":
    main()
