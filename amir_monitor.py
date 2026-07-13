#!/usr/bin/env python3
"""
📊 Amir Data Freshness Monitor
Monitors data freshness from Amir's Windows MT5 server
Alerts when data is stale and integrates with Pattern JSON system
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List
import psycopg2
import psycopg2.extras
import logging

# Add patterns directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))
from common import get_pg_conn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('amir_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AmirDataMonitor:
    """Monitor data freshness from Amir's MT5 server"""
    
    def __init__(self):
        self.symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
        self.alert_thresholds = {
            'stale_data_minutes': 5,      # Alert if data older than 5 minutes
            'missing_data_minutes': 10,   # Alert if no data for 10 minutes
            'spread_anomaly_factor': 3.0, # Alert if spread 3x normal
            'connection_timeout_minutes': 15  # Alert if no connection for 15 minutes
        }
        self.last_alerts = {}
        self.alert_cooldown = 300  # 5 minutes between same alerts
        
    def run_continuous_monitoring(self):
        """Run continuous monitoring of Amir's data"""
        logger.info("🔍 Starting Amir Data Freshness Monitor...")
        logger.info(f"📊 Monitoring symbols: {', '.join(self.symbols)}")
        logger.info(f"⚠️  Alert thresholds: {self.alert_thresholds}")
        
        while True:
            try:
                # Check data freshness for each symbol
                freshness_report = self.check_data_freshness()
                
                # Check connection health
                connection_health = self.check_connection_health()
                
                # Check spread anomalies
                spread_anomalies = self.check_spread_anomalies()
                
                # Generate comprehensive status report
                status_report = self.generate_status_report(
                    freshness_report, connection_health, spread_anomalies
                )
                
                # Process alerts if needed
                self.process_alerts(status_report)
                
                # Log status summary
                self.log_status_summary(status_report)
                
                # Update monitoring database
                self.update_monitoring_database(status_report)
                
                # Sleep for 1 minute before next check
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitor error: {str(e)}")
                time.sleep(30)  # Wait before retrying
    
    def check_data_freshness(self) -> Dict:
        """Check data freshness for all symbols"""
        freshness_report = {}
        
        try:
            conn = get_pg_conn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            for symbol in self.symbols:
                # Get latest data for symbol
                query = """
                SELECT 
                    symbol,
                    open_time,
                    spread,
                    volume,
                    mt5_collection_time,
                    data_source,
                    trading_session,
                    EXTRACT(EPOCH FROM (NOW() - open_time))/60 as minutes_since_data,
                    EXTRACT(EPOCH FROM (NOW() - COALESCE(mt5_collection_time, open_time)))/60 as minutes_since_collection
                FROM ohlc_data 
                WHERE symbol = %s 
                ORDER BY open_time DESC 
                LIMIT 1
                """
                
                cursor.execute(query, (symbol,))
                result = cursor.fetchone()
                
                if result:
                    freshness_report[symbol] = {
                        'latest_data_time': result['open_time'],
                        'minutes_since_data': float(result['minutes_since_data'] or 0),
                        'minutes_since_collection': float(result['minutes_since_collection'] or 0),
                        'spread': float(result['spread'] or 0),
                        'volume': int(result['volume'] or 0),
                        'data_source': result['data_source'],
                        'trading_session': result['trading_session'],
                        'is_fresh': float(result['minutes_since_data'] or 0) <= self.alert_thresholds['stale_data_minutes'],
                        'is_connected': float(result['minutes_since_collection'] or 0) <= self.alert_thresholds['connection_timeout_minutes']
                    }
                else:
                    freshness_report[symbol] = {
                        'latest_data_time': None,
                        'minutes_since_data': float('inf'),
                        'minutes_since_collection': float('inf'),
                        'spread': 0,
                        'volume': 0,
                        'data_source': 'unknown',
                        'trading_session': 'unknown',
                        'is_fresh': False,
                        'is_connected': False
                    }
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error checking data freshness: {str(e)}")
            
        return freshness_report
    
    def check_connection_health(self) -> Dict:
        """Check overall connection health with Amir's server"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            
            # Check total records in last hour
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT symbol) as symbols_with_data,
                    MAX(open_time) as latest_data,
                    MIN(open_time) as earliest_data_hour
                FROM ohlc_data 
                WHERE open_time >= NOW() - INTERVAL '1 hour'
            """)
            
            result = cursor.fetchone()
            
            # Check for Amir-specific data source
            cursor.execute("""
                SELECT COUNT(*) 
                FROM ohlc_data 
                WHERE data_source LIKE '%amir%' 
                    AND open_time >= NOW() - INTERVAL '1 hour'
            """)
            
            amir_records = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_records_last_hour': result[0],
                'symbols_active': result[1],
                'latest_data_time': result[2],
                'amir_specific_records': amir_records,
                'connection_healthy': result[0] > 0 and result[1] >= len(self.symbols) * 0.8
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking connection health: {str(e)}")
            return {'connection_healthy': False}
    
    def check_spread_anomalies(self) -> Dict:
        """Check for spread anomalies that might indicate data issues"""
        anomalies = {}
        
        try:
            conn = get_pg_conn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            for symbol in self.symbols:
                # Get recent spread data
                query = """
                SELECT 
                    spread,
                    open_time,
                    AVG(spread) OVER (PARTITION BY symbol ORDER BY open_time ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING) as avg_spread
                FROM ohlc_data 
                WHERE symbol = %s 
                    AND spread > 0 
                    AND open_time >= NOW() - INTERVAL '1 hour'
                ORDER BY open_time DESC 
                LIMIT 5
                """
                
                cursor.execute(query, (symbol,))
                results = cursor.fetchall()
                
                if results:
                    latest_spread = float(results[0]['spread'])
                    avg_spread = float(results[0]['avg_spread'] or latest_spread)
                    
                    # Check for anomalies
                    is_anomaly = (latest_spread > avg_spread * self.alert_thresholds['spread_anomaly_factor'] 
                                 if avg_spread > 0 else False)
                    
                    anomalies[symbol] = {
                        'latest_spread': latest_spread,
                        'average_spread': avg_spread,
                        'is_anomaly': is_anomaly,
                        'anomaly_factor': latest_spread / avg_spread if avg_spread > 0 else 0
                    }
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error checking spread anomalies: {str(e)}")
            
        return anomalies
    
    def generate_status_report(self, freshness_report: Dict, connection_health: Dict, spread_anomalies: Dict) -> Dict:
        """Generate comprehensive status report"""
        current_time = datetime.now()
        
        # Count fresh vs stale symbols
        fresh_symbols = sum(1 for data in freshness_report.values() if data['is_fresh'])
        connected_symbols = sum(1 for data in freshness_report.values() if data['is_connected'])
        anomaly_symbols = sum(1 for data in spread_anomalies.values() if data.get('is_anomaly', False))
        
        # Determine overall health
        overall_health = 'healthy'
        if fresh_symbols < len(self.symbols) * 0.8:
            overall_health = 'degraded'
        if fresh_symbols < len(self.symbols) * 0.5:
            overall_health = 'critical'
        
        return {
            'timestamp': current_time,
            'overall_health': overall_health,
            'symbols_fresh': fresh_symbols,
            'symbols_connected': connected_symbols,
            'symbols_with_anomalies': anomaly_symbols,
            'total_symbols': len(self.symbols),
            'freshness_report': freshness_report,
            'connection_health': connection_health,
            'spread_anomalies': spread_anomalies,
            'alerts_needed': self.determine_alerts_needed(freshness_report, connection_health, spread_anomalies)
        }
    
    def determine_alerts_needed(self, freshness_report: Dict, connection_health: Dict, spread_anomalies: Dict) -> List[Dict]:
        """Determine what alerts need to be sent"""
        alerts = []
        
        # Check for stale data alerts
        for symbol, data in freshness_report.items():
            if not data['is_fresh']:
                alerts.append({
                    'type': 'stale_data',
                    'symbol': symbol,
                    'severity': 'warning' if data['minutes_since_data'] < 10 else 'critical',
                    'message': f"Stale data for {symbol}: {data['minutes_since_data']:.1f} minutes old",
                    'details': data
                })
        
        # Check for connection alerts
        if not connection_health.get('connection_healthy', False):
            alerts.append({
                'type': 'connection_issue',
                'symbol': 'ALL',
                'severity': 'critical',
                'message': f"Connection issues detected. Only {connection_health.get('symbols_active', 0)} symbols active",
                'details': connection_health
            })
        
        # Check for spread anomaly alerts
        for symbol, data in spread_anomalies.items():
            if data.get('is_anomaly', False):
                alerts.append({
                    'type': 'spread_anomaly',
                    'symbol': symbol,
                    'severity': 'warning',
                    'message': f"Spread anomaly for {symbol}: {data['latest_spread']:.5f} vs avg {data['average_spread']:.5f}",
                    'details': data
                })
        
        return alerts
    
    def process_alerts(self, status_report: Dict):
        """Process and send alerts if needed"""
        alerts = status_report.get('alerts_needed', [])
        current_time = datetime.now()
        
        for alert in alerts:
            alert_key = f"{alert['type']}_{alert['symbol']}"
            
            # Check cooldown
            last_alert_time = self.last_alerts.get(alert_key)
            if last_alert_time and (current_time - last_alert_time).seconds < self.alert_cooldown:
                continue
            
            # Send alert
            self.send_alert(alert)
            self.last_alerts[alert_key] = current_time
    
    def send_alert(self, alert: Dict):
        """Send alert notification"""
        # Log alert
        severity_emoji = "🚨" if alert['severity'] == 'critical' else "⚠️"
        logger.warning(f"{severity_emoji} ALERT: {alert['message']}")
        
        # You can extend this to send email, Slack, or other notifications
        # Example: send_email_alert(alert)
        # Example: send_slack_alert(alert)
    
    def log_status_summary(self, status_report: Dict):
        """Log summary of current status"""
        health_emoji = {
            'healthy': '✅',
            'degraded': '⚠️',
            'critical': '🚨'
        }[status_report['overall_health']]
        
        logger.info(f"{health_emoji} System Health: {status_report['overall_health'].upper()} - "
                   f"{status_report['symbols_fresh']}/{status_report['total_symbols']} symbols fresh, "
                   f"{status_report['symbols_connected']}/{status_report['total_symbols']} connected")
    
    def update_monitoring_database(self, status_report: Dict):
        """Store monitoring data in database"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            
            # Create monitoring table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS amir_monitoring_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    overall_health VARCHAR(20),
                    symbols_fresh INTEGER,
                    symbols_connected INTEGER,
                    symbols_with_anomalies INTEGER,
                    total_symbols INTEGER,
                    alerts_count INTEGER,
                    status_data JSONB
                )
            """)
            
            # Insert current status
            cursor.execute("""
                INSERT INTO amir_monitoring_log (
                    overall_health, symbols_fresh, symbols_connected, 
                    symbols_with_anomalies, total_symbols, alerts_count, status_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                status_report['overall_health'],
                status_report['symbols_fresh'],
                status_report['symbols_connected'],
                status_report['symbols_with_anomalies'],
                status_report['total_symbols'],
                len(status_report['alerts_needed']),
                json.dumps(status_report, default=str)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error updating monitoring database: {str(e)}")
    
    def get_monitoring_dashboard_data(self) -> Dict:
        """Get data for monitoring dashboard"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Get recent monitoring history
            cursor.execute("""
                SELECT * FROM amir_monitoring_log 
                ORDER BY timestamp DESC 
                LIMIT 24
            """)
            recent_logs = cursor.fetchall()
            
            # Get current symbol status
            freshness_report = self.check_data_freshness()
            
            conn.close()
            
            return {
                'current_status': freshness_report,
                'recent_logs': [dict(log) for log in recent_logs],
                'dashboard_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting dashboard data: {str(e)}")
            return {}

def run_quick_health_check():
    """Run a quick health check and return results"""
    monitor = AmirDataMonitor()
    
    print("🔍 Running Amir Data Health Check...")
    print("=" * 50)
    
    # Check data freshness
    freshness_report = monitor.check_data_freshness()
    connection_health = monitor.check_connection_health()
    spread_anomalies = monitor.check_spread_anomalies()
    
    status_report = monitor.generate_status_report(
        freshness_report, connection_health, spread_anomalies
    )
    
    # Print results
    health_emoji = {
        'healthy': '✅',
        'degraded': '⚠️',
        'critical': '🚨'
    }[status_report['overall_health']]
    
    print(f"{health_emoji} Overall Health: {status_report['overall_health'].upper()}")
    print(f"📊 Fresh Symbols: {status_report['symbols_fresh']}/{status_report['total_symbols']}")
    print(f"🔗 Connected Symbols: {status_report['symbols_connected']}/{status_report['total_symbols']}")
    print(f"⚠️  Anomalies: {status_report['symbols_with_anomalies']} symbols")
    
    print("\n📈 Symbol Details:")
    for symbol, data in freshness_report.items():
        status_emoji = "✅" if data['is_fresh'] else "❌"
        print(f"   {status_emoji} {symbol}: {data['minutes_since_data']:.1f}min old, "
              f"spread={data['spread']:.5f}")
    
    # Print alerts
    if status_report['alerts_needed']:
        print("\n🚨 Active Alerts:")
        for alert in status_report['alerts_needed']:
            severity_emoji = "🚨" if alert['severity'] == 'critical' else "⚠️"
            print(f"   {severity_emoji} {alert['message']}")
    else:
        print("\n✅ No active alerts")
    
    return status_report

def main():
    """Main monitoring execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Amir Data Freshness Monitor')
    parser.add_argument('--check', action='store_true', help='Run single health check')
    parser.add_argument('--monitor', action='store_true', help='Run continuous monitoring')
    
    args = parser.parse_args()
    
    if args.check:
        run_quick_health_check()
    elif args.monitor:
        monitor = AmirDataMonitor()
        monitor.run_continuous_monitoring()
    else:
        print("🔍 Amir Data Freshness Monitor")
        print("Usage:")
        print("  python3 amir_monitor.py --check     # Quick health check")
        print("  python3 amir_monitor.py --monitor   # Continuous monitoring")

if __name__ == "__main__":
    main()
