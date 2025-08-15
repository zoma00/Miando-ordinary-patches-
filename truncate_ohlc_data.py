#!/usr/bin/env python3
"""
Script to truncate OHLC data table
This will remove ALL data from the ohlc_data table
"""

import os
import sys
from sqlalchemy import create_engine, text

# ==================== CONFIG ====================
DB_HOST = os.getenv('DB_HOST', 'miando-db')
DB_PORT = os.getenv('DB_PORT', '5434')
DB_NAME = os.getenv('DB_NAME', 'miando')
DB_USER = os.getenv('DB_USER', 'miando')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'changeme')
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', '/app/server.crt')

# ==================== DB URL ====================
if os.path.exists(SSL_CERT_PATH):
    DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require&sslrootcert={SSL_CERT_PATH}"
else:
    print("⚠️ SSL-Zertifikat nicht gefunden – Verbindung ohne SSL.")
    DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def truncate_ohlc_data():
    """Truncate the ohlc_data table - removes ALL data"""
    print(f"🔗 Connecting to DB {DB_HOST}:{DB_PORT}/{DB_NAME}")
    engine = create_engine(DB_URL, isolation_level="AUTOCOMMIT")
    
    try:
        with engine.connect() as conn:
            # First check how many records exist
            count_result = conn.execute(text("SELECT COUNT(*) FROM ohlc_data")).scalar()
            print(f"📊 Current records in ohlc_data: {count_result:,}")
            
            if count_result == 0:
                print("✅ Table is already empty")
                return
            
            # Confirm truncation
            confirm = input(f"\n⚠️ WARNING: This will DELETE ALL {count_result:,} records from ohlc_data table!\nType 'YES' to confirm: ")
            
            if confirm != 'YES':
                print("❌ Operation cancelled")
                return
            
            print("🗑️ Truncating ohlc_data table...")
            
            # Truncate the table (faster than DELETE)
            conn.execute(text("TRUNCATE TABLE ohlc_data RESTART IDENTITY"))
            
            # Verify truncation
            final_count = conn.execute(text("SELECT COUNT(*) FROM ohlc_data")).scalar()
            print(f"✅ Truncation complete. Records remaining: {final_count}")
            
            if final_count == 0:
                print("🎯 OHLC data table successfully truncated!")
            else:
                print(f"⚠️ Warning: {final_count} records still remain")
                
    except Exception as e:
        print(f"❌ Error truncating table: {e}")
        sys.exit(1)

def show_table_info():
    """Show current table statistics"""
    print(f"🔗 Connecting to DB {DB_HOST}:{DB_PORT}/{DB_NAME}")
    engine = create_engine(DB_URL, isolation_level="AUTOCOMMIT")
    
    try:
        with engine.connect() as conn:
            # Total records
            total = conn.execute(text("SELECT COUNT(*) FROM ohlc_data")).scalar()
            print(f"📊 Total records: {total:,}")
            
            if total > 0:
                # Records by symbol
                symbol_counts = conn.execute(text("""
                    SELECT symbol, COUNT(*) as count 
                    FROM ohlc_data 
                    GROUP BY symbol 
                    ORDER BY count DESC
                """)).fetchall()
                
                print("\n📈 Records by symbol:")
                for symbol, count in symbol_counts:
                    print(f"  {symbol}: {count:,}")
                
                # Records by timeframe
                tf_counts = conn.execute(text("""
                    SELECT timeframe, COUNT(*) as count 
                    FROM ohlc_data 
                    GROUP BY timeframe 
                    ORDER BY count DESC
                """)).fetchall()
                
                print("\n⏰ Records by timeframe:")
                for tf, count in tf_counts:
                    print(f"  {tf}: {count:,}")
                
                # Date range
                date_range = conn.execute(text("""
                    SELECT 
                        MIN(open_time) as earliest,
                        MAX(open_time) as latest
                    FROM ohlc_data
                """)).fetchone()
                
                print(f"\n📅 Date range: {date_range.earliest} to {date_range.latest}")
            
    except Exception as e:
        print(f"❌ Error getting table info: {e}")

if __name__ == "__main__":
    print("🚀 OHLC Data Management Tool")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        show_table_info()
    elif len(sys.argv) > 1 and sys.argv[1] == "--force":
        # Force truncate without confirmation (dangerous!)
        print("🔗 Connecting to DB...")
        engine = create_engine(DB_URL, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM ohlc_data")).scalar()
            print(f"🗑️ Force truncating {count:,} records...")
            conn.execute(text("TRUNCATE TABLE ohlc_data RESTART IDENTITY"))
            print("✅ Force truncation complete!")
    else:
        show_table_info()
        print("\nOptions:")
        print("  python truncate_ohlc_data.py --info    # Show table info only")
        print("  python truncate_ohlc_data.py           # Interactive truncate")
        print("  python truncate_ohlc_data.py --force   # Force truncate (no confirmation)")
        print()
        
        if input("Do you want to truncate the table? (y/N): ").lower() == 'y':
            truncate_ohlc_data()
