#!/usr/bin/env python3
"""
🌉 Miando Data Bridge - Amir Integration
Bridges data from Amir's Windows MT5 server to enhance Pattern JSON system
Works with existing database schema and Amir's data collection
"""

import sys
import os
import time
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import psycopg2
import psycopg2.extras

# Add patterns directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))
from common import get_pg_conn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('amir_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AmirDataBridge:
    """Bridge between Amir's MT5 data and Miando Pattern JSON system"""
    
    def __init__(self):
        self.last_processed_time = {}
        self.symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
        self.running = True
        
    def start_monitoring(self):
        """Start continuous monitoring of Amir's data"""
        logger.info("🚀 Starting Amir Data Bridge...")
        logger.info(f"📊 Monitoring symbols: {', '.join(self.symbols)}")
        
        while self.running:
            try:
                # Check for new OHLC data from Amir
                self.process_new_ohlc_data()
                
                # Check for new account state from Amir
                self.process_account_updates()
                
                # Check for new trade data from Amir
                self.process_trade_updates()
                
                # Update Pattern JSON freshness
                self.update_pattern_json_freshness()
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bridge stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"❌ Bridge error: {str(e)}")
                time.sleep(10)  # Wait before retrying
    
    def process_new_ohlc_data(self):
        """Process new OHLC data from Amir's collection"""
        conn = get_pg_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        for symbol in self.symbols:
            try:
                # Get latest data for this symbol
                last_processed = self.last_processed_time.get(f"ohlc_{symbol}", 
                                                            datetime.now() - timedelta(hours=1))
                
                query = """
                SELECT * FROM ohlc_data 
                WHERE symbol = %s 
                    AND open_time > %s 
                ORDER BY open_time DESC 
                LIMIT 10
                """
                
                cursor.execute(query, (symbol, last_processed))
                new_records = cursor.fetchall()
                
                if new_records:
                    logger.info(f"📈 Processing {len(new_records)} new OHLC records for {symbol}")
                    
                    for record in new_records:
                        # Enhance the record with additional data
                        enhanced_data = self.enhance_ohlc_record(record)
                        
                        # Update the record with enhancements
                        self.update_ohlc_with_enhancements(cursor, enhanced_data)
                        
                        # Track processing time
                        self.last_processed_time[f"ohlc_{symbol}"] = record['open_time']
                    
                    conn.commit()
                    logger.info(f"✅ Enhanced {len(new_records)} records for {symbol}")
                        
            except Exception as e:
                logger.error(f"❌ Error processing OHLC for {symbol}: {str(e)}")
        
        conn.close()
    
    def enhance_ohlc_record(self, record: Dict) -> Dict:
        """Enhance OHLC record with additional analysis"""
        enhanced = dict(record)
        
        # Calculate spread if not present
        if not record.get('spread') or record['spread'] == 0:
            # Estimate spread based on symbol (fallback)
            spread_estimates = {
                'XAUUSD': 0.30,
                'EURUSD': 0.00015,
                'GBPUSD': 0.00020,
                'USDJPY': 0.015,
                'USDCHF': 0.00018
            }
            enhanced['estimated_spread'] = spread_estimates.get(record['symbol'], 0.0001)
        
        # Determine trading session
        enhanced['trading_session'] = self.get_trading_session(record['open_time'])
        
        # Calculate volatility indicator
        enhanced['volatility_score'] = self.calculate_volatility_score(record)
        
        # Add data freshness timestamp
        enhanced['bridge_processed_at'] = datetime.now()
        
        # Calculate price change percentage
        if record['open_price'] and record['close_price']:
            price_change = ((record['close_price'] - record['open_price']) / record['open_price']) * 100
            enhanced['price_change_pct'] = round(price_change, 4)
        
        return enhanced
    
    def get_trading_session(self, timestamp: datetime) -> str:
        """Determine trading session based on UTC time"""
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Convert to UTC if timezone-aware
        if timestamp.tzinfo:
            utc_time = timestamp.astimezone(timezone.utc)
        else:
            utc_time = timestamp
        
        hour = utc_time.hour
        
        # Session mapping (UTC hours)
        if 22 <= hour or hour < 7:
            return 'Sydney'
        elif 8 <= hour < 17:
            return 'London'
        elif 13 <= hour < 22:
            return 'New_York'
        else:
            return 'Transition'
    
    def calculate_volatility_score(self, record: Dict) -> float:
        """Calculate simple volatility score"""
        if not all([record.get('high_price'), record.get('low_price'), record.get('open_price')]):
            return 0.0
        
        # Calculate range as percentage of open price
        price_range = record['high_price'] - record['low_price']
        if record['open_price'] > 0:
            volatility = (price_range / record['open_price']) * 100
            return round(volatility, 4)
        return 0.0
    
    def update_ohlc_with_enhancements(self, cursor, enhanced_data: Dict):
        """Update OHLC record with bridge enhancements"""
        # Create metadata JSON for bridge data
        bridge_metadata = {
            'trading_session': enhanced_data.get('trading_session'),
            'volatility_score': enhanced_data.get('volatility_score'),
            'price_change_pct': enhanced_data.get('price_change_pct'),
            'estimated_spread': enhanced_data.get('estimated_spread'),
            'bridge_processed_at': enhanced_data['bridge_processed_at'].isoformat()
        }
        
        # Store bridge metadata in a comment or separate field
        # Since we're working with existing schema, we'll log this info
        logger.info(f"📊 Enhanced data for {enhanced_data['symbol']} at {enhanced_data['open_time']}: "
                   f"Session={enhanced_data['trading_session']}, "
                   f"Volatility={enhanced_data.get('volatility_score', 0):.4f}%")
    
    def process_account_updates(self):
        """Process new account state updates from Amir"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Get latest account state
            last_processed = self.last_processed_time.get('account', 
                                                        datetime.now() - timedelta(hours=1))
            
            query = """
            SELECT * FROM account_state 
            WHERE timestamp > %s 
            ORDER BY timestamp DESC 
            LIMIT 5
            """
            
            cursor.execute(query, (last_processed,))
            new_records = cursor.fetchall()
            
            if new_records:
                logger.info(f"💰 Processing {len(new_records)} new account updates")
                
                for record in new_records:
                    # Analyze account performance
                    self.analyze_account_performance(record)
                    self.last_processed_time['account'] = record['timestamp']
                
                logger.info("✅ Account updates processed")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error processing account updates: {str(e)}")
    
    def analyze_account_performance(self, account_record: Dict):
        """Analyze account performance from Amir's data"""
        # Log key account metrics
        balance = account_record.get('balance', 0)
        equity = account_record.get('equity', 0)
        profit = account_record.get('profit', 0)
        
        # Calculate account health score
        if balance > 0:
            equity_ratio = (equity / balance) * 100
            profit_ratio = (profit / balance) * 100
            
            logger.info(f"📊 Account Health: Equity={equity_ratio:.2f}%, "
                       f"Profit={profit_ratio:.2f}%, Balance=${balance:.2f}")
    
    def process_trade_updates(self):
        """Process new trade updates from Amir"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Check for new open trades
            last_processed = self.last_processed_time.get('trades', 
                                                        datetime.now() - timedelta(hours=1))
            
            query = """
            SELECT * FROM open_trades 
            WHERE open_time > %s 
            ORDER BY open_time DESC 
            LIMIT 10
            """
            
            cursor.execute(query, (last_processed,))
            new_trades = cursor.fetchall()
            
            if new_trades:
                logger.info(f"📊 Processing {len(new_trades)} new trades")
                
                for trade in new_trades:
                    self.analyze_trade_setup(trade)
                    self.last_processed_time['trades'] = trade['open_time']
            
            # Check for recently closed trades
            query = """
            SELECT * FROM closed_trades 
            WHERE time > %s 
            ORDER BY time DESC 
            LIMIT 10
            """
            
            cursor.execute(query, (last_processed,))
            closed_trades = cursor.fetchall()
            
            if closed_trades:
                logger.info(f"🏁 Processing {len(closed_trades)} closed trades")
                
                for trade in closed_trades:
                    self.analyze_trade_result(trade)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error processing trade updates: {str(e)}")
    
    def analyze_trade_setup(self, trade_record: Dict):
        """Analyze trade setup from Amir's trading data"""
        symbol = trade_record.get('symbol')
        trade_type = trade_record.get('order_type', trade_record.get('type', 'Unknown'))
        lot_size = trade_record.get('lot_size', trade_record.get('volume', 0))
        
        logger.info(f"📈 New Trade: {symbol} {trade_type} {lot_size} lots at {trade_record.get('open_price')}")
    
    def analyze_trade_result(self, trade_record: Dict):
        """Analyze closed trade results"""
        symbol = trade_record.get('symbol')
        profit = trade_record.get('profit', 0)
        
        result_emoji = "✅" if profit > 0 else "❌" if profit < 0 else "➖"
        logger.info(f"{result_emoji} Closed Trade: {symbol} P&L=${profit:.2f}")
    
    def update_pattern_json_freshness(self):
        """Update Pattern JSON system with fresh data indicators"""
        try:
            # This integrates with your existing force-fresh system
            for symbol in self.symbols:
                # Check if we have fresh data for this symbol
                fresh_data_available = self.check_fresh_data_availability(symbol)
                
                if fresh_data_available:
                    # Signal that fresh data is available for Pattern JSON
                    self.signal_fresh_data_available(symbol)
        
        except Exception as e:
            logger.error(f"❌ Error updating Pattern JSON freshness: {str(e)}")
    
    def check_fresh_data_availability(self, symbol: str) -> bool:
        """Check if fresh data is available from Amir's collection"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            
            # Check for data within last 2 minutes
            query = """
            SELECT COUNT(*) FROM ohlc_data 
            WHERE symbol = %s 
                AND open_time > NOW() - INTERVAL '2 minutes'
            """
            
            cursor.execute(query, (symbol,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
            
        except Exception as e:
            logger.error(f"❌ Error checking fresh data for {symbol}: {str(e)}")
            return False
    
    def signal_fresh_data_available(self, symbol: str):
        """Signal that fresh data is available for Pattern JSON generation"""
        # This can trigger your force-fresh Pattern JSON generation
        logger.info(f"🔄 Fresh data available for {symbol} - ready for Pattern JSON generation")
        
        # You can extend this to trigger actual Pattern JSON generation
        # from patterns.json_split.pattern_json_live import build_pattern_json
        # pattern_json = build_pattern_json(symbol, force_fresh=True)
    
    def get_bridge_status(self) -> Dict:
        """Get bridge system status"""
        return {
            'bridge_active': self.running,
            'symbols_monitored': self.symbols,
            'last_processed_times': self.last_processed_time,
            'status_timestamp': datetime.now().isoformat()
        }

def main():
    """Main bridge execution"""
    print("🌉 Miando Data Bridge - Amir Integration")
    print("=" * 50)
    
    bridge = AmirDataBridge()
    
    try:
        bridge.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Bridge stopped by user")
    except Exception as e:
        print(f"❌ Bridge crashed: {str(e)}")
        logger.error(f"Bridge crashed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
