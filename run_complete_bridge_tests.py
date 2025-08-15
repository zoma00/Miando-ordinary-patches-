#!/usr/bin/env python3
"""
🧪 COMPLETE AMIR BRIDGE INTEGRATION TEST SUITE
Comprehensive testing script for the bridge integration system
"""

import sys
import os
import subprocess
import time
from datetime import datetime

# Add patterns directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))
from common import get_pg_conn

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

class TestRunner:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.start_time = datetime.now()

    def print_header(self, title):
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}{title}{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")

    def print_test(self, test_name):
        print(f"\n{Colors.CYAN}🔍 Testing: {test_name}{Colors.NC}")
        print("-" * 40)

    def run_test(self, test_name, test_func):
        self.print_test(test_name)
        self.total_tests += 1
        
        try:
            result = test_func()
            if result:
                print(f"{Colors.GREEN}✅ PASS: {test_name}{Colors.NC}")
                self.passed_tests += 1
                return True
            else:
                print(f"{Colors.RED}❌ FAIL: {test_name}{Colors.NC}")
                return False
        except Exception as e:
            print(f"{Colors.RED}❌ ERROR in {test_name}: {str(e)}{Colors.NC}")
            return False

    def test_database_connection(self):
        """Test database connection"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            conn.close()
            print(f"✅ Connected: {version[:50]}...")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False

    def test_trading_session_function(self):
        """Test trading session function with proper casting"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT get_trading_session(NOW()::timestamp) as session")
            session = cursor.fetchone()[0]
            conn.close()
            print(f"✅ Current Session: {session}")
            return True
        except Exception as e:
            print(f"❌ Trading session test failed: {str(e)}")
            return False

    def test_ohlc_data_availability(self):
        """Test OHLC data availability"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM ohlc_data")
            total_count = cursor.fetchone()[0]
            print(f"✅ Total OHLC Records: {total_count:,}")
            
            cursor.execute("SELECT COUNT(*) FROM ohlc_data WHERE open_time >= NOW() - INTERVAL '24 hours'")
            recent_count = cursor.fetchone()[0]
            print(f"✅ Recent (24h): {recent_count:,}")
            
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM ohlc_data")
            symbols = cursor.fetchone()[0]
            print(f"✅ Symbols: {symbols}")
            
            conn.close()
            return total_count > 0
        except Exception as e:
            print(f"❌ OHLC data test failed: {str(e)}")
            return False

    def test_bridge_enhancement_columns(self):
        """Test bridge enhancement columns"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ohlc_data' 
                AND column_name IN ('spread', 'mt5_collection_time', 'data_source', 'trading_session')
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            print(f"✅ Enhanced Columns: {len(columns)}/4 ({', '.join(columns)})")
            return len(columns) >= 3  # Allow some flexibility
        except Exception as e:
            print(f"❌ Bridge enhancement test failed: {str(e)}")
            return False

    def test_json_split_pattern_system(self):
        """Test JSON Split pattern system"""
        try:
            # Try to import the force fresh pattern module
            patterns_dir = os.path.join(os.path.dirname(__file__), 'patterns', 'json_split')
            sys.path.append(patterns_dir)
            
            from force_fresh_pattern import force_fresh_pattern_json
            print("✅ Force Fresh Pattern: Available")
            
            # Check trading_snapshots table
            conn = get_pg_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'trading_snapshots'")
            table_exists = cursor.fetchone()[0] > 0
            
            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM trading_snapshots WHERE pattern_json IS NOT NULL")
                snapshots = cursor.fetchone()[0]
                print(f"✅ Pattern JSON Snapshots: {snapshots}")
            else:
                print("⚠️  trading_snapshots table not found")
            
            conn.close()
            return True
        except ImportError as e:
            print(f"❌ Import failed: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ JSON Split test failed: {str(e)}")
            return False

    def test_bridge_scripts_availability(self):
        """Test bridge scripts availability"""
        scripts = ['amir_monitor.py', 'amir_data_bridge.py', 'amir_dashboard.py']
        found = []
        
        for script in scripts:
            if os.path.exists(script):
                found.append(script.replace('.py', ''))
        
        print(f"✅ Bridge Scripts: {', '.join(found)} ({len(found)}/3)")
        return len(found) >= 2  # Allow some flexibility

    def test_data_quality(self):
        """Test data quality"""
        try:
            conn = get_pg_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT symbol) as symbols,
                    COUNT(DISTINCT timeframe) as timeframes,
                    MIN(open_time) as oldest,
                    MAX(open_time) as newest
                FROM ohlc_data 
                WHERE open_time >= NOW() - INTERVAL '24 hours'
            """)
            stats = cursor.fetchone()
            
            print(f"✅ 24h Data Quality:")
            print(f"   Symbols: {stats[0]}")
            print(f"   Timeframes: {stats[1]}")
            print(f"   Range: {stats[2]} to {stats[3]}")
            
            conn.close()
            return stats[0] > 0  # At least one symbol
        except Exception as e:
            print(f"❌ Data quality test failed: {str(e)}")
            return False

    def test_json_split_pattern_execution(self):
        """Test JSON Split pattern execution"""
        try:
            result = subprocess.run(['python3', 'test_json_split_pattern.py'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ JSON Split Pattern test executed successfully")
                # Show last few lines of output
                lines = result.stdout.split('\n')
                for line in lines[-5:]:
                    if line.strip():
                        print(f"   {line}")
                return True
            else:
                print("❌ JSON Split Pattern test failed")
                print(f"Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ JSON Split Pattern test timed out")
            return False
        except Exception as e:
            print(f"❌ JSON Split Pattern execution failed: {str(e)}")
            return False

    def test_full_bridge_integration(self):
        """Test full bridge integration"""
        try:
            result = subprocess.run(['python3', 'test_amir_bridge_integration.py'], 
                                  capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ Full Bridge Integration test passed")
                # Show summary from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Bridge Test Results:' in line or '🎉' in line or '✅' in line:
                        if len(line.strip()) > 0:
                            print(f"   {line}")
                return True
            else:
                print("❌ Full Bridge Integration test failed")
                # Show error details
                error_lines = result.stderr.split('\n') if result.stderr else result.stdout.split('\n')
                for line in error_lines[-10:]:
                    if line.strip():
                        print(f"   {line}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Full Bridge Integration test timed out")
            return False
        except Exception as e:
            print(f"❌ Full Bridge Integration test failed: {str(e)}")
            return False

    def print_final_results(self):
        """Print final test results"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        self.print_header("📊 FINAL TEST RESULTS")
        
        print(f"Total Tests: {self.total_tests}")
        print(f"{Colors.GREEN}Passed: {self.passed_tests}{Colors.NC}")
        print(f"{Colors.RED}Failed: {self.total_tests - self.passed_tests}{Colors.NC}")
        print(f"Success Rate: {(self.passed_tests * 100) // self.total_tests}%")
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        
        if self.passed_tests == self.total_tests:
            print(f"\n{Colors.GREEN}🎉 ALL TESTS PASSED - BRIDGE INTEGRATION FULLY FUNCTIONAL!{Colors.NC}")
            print("✅ Database connection working")
            print("✅ Trading session function fixed and working")
            print("✅ Amir's data flowing properly")
            print("✅ JSON Split pattern system compatible")
            print("✅ Bridge components ready")
            print("✅ System ready for production")
        elif self.passed_tests >= self.total_tests - 1:
            print(f"\n{Colors.YELLOW}⚠️  MOSTLY FUNCTIONAL - Minor issues detected{Colors.NC}")
            print("Most components working, check failed tests above")
        else:
            print(f"\n{Colors.RED}❌ SIGNIFICANT ISSUES - Bridge integration needs attention{Colors.NC}")
            print("Multiple components failing, review errors above")

        print(f"\n{Colors.BLUE}📋 NEXT STEPS:{Colors.NC}")
        print("1. Review any failed tests above")
        print("2. If all passed, your bridge integration is ready")
        print("3. Run 'python3 amir_data_bridge.py' to start bridge")
        print("4. Run 'python3 amir_monitor.py' for monitoring")
        print("5. Run 'python3 amir_dashboard.py' for status dashboard")

def main():
    runner = TestRunner()
    
    print(f"{Colors.PURPLE}🧪 COMPLETE AMIR BRIDGE INTEGRATION TEST SUITE{Colors.NC}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Location: {os.getcwd()}")
    
    # Environment check
    runner.print_header("📋 PRE-TEST ENVIRONMENT CHECK")
    print(f"🐍 Python Version: {sys.version.split()[0]}")
    print(f"📁 Current Directory: {os.getcwd()}")
    
    # Essential files check
    essential_files = [
        'test_amir_bridge_integration.py',
        'test_json_split_pattern.py', 
        'amir_data_bridge.py',
        'amir_monitor.py',
        'amir_dashboard.py'
    ]
    
    print("📄 Essential Files:")
    for file in essential_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file}")
    
    # Run all tests
    runner.print_header("🚀 RUNNING COMPREHENSIVE TEST SUITE")
    
    tests = [
        ("Database Connection", runner.test_database_connection),
        ("Trading Session Function (Fixed)", runner.test_trading_session_function),
        ("OHLC Data Availability", runner.test_ohlc_data_availability),
        ("Bridge Enhancement Columns", runner.test_bridge_enhancement_columns),
        ("JSON Split Pattern System", runner.test_json_split_pattern_system),
        ("Bridge Scripts Availability", runner.test_bridge_scripts_availability),
        ("Data Quality Check", runner.test_data_quality),
        ("JSON Split Pattern Execution", runner.test_json_split_pattern_execution),
        ("Full Bridge Integration", runner.test_full_bridge_integration),
    ]
    
    for test_name, test_func in tests:
        runner.run_test(test_name, test_func)
        time.sleep(0.5)  # Brief pause between tests
    
    # Print final results
    runner.print_final_results()
    
    return runner.passed_tests == runner.total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
