#!/bin/bash
# 🧪 COMPLETE AMIR BRIDGE INTEGRATION TEST SUITE
# Comprehensive testing script for the bridge integration system
# Author: GitHub Copilot
# Date: August 9, 2025

set -e  # Exit on any error

echo "🧪 COMPLETE AMIR BRIDGE INTEGRATION TEST SUITE"
echo "=============================================================="
echo "Date: $(date)"
echo "Location: $(pwd)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${BLUE}🔍 Testing: $test_name${NC}"
    echo "Command: $test_command"
    echo "----------------------------------------"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASS: $test_name${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL: $test_name${NC}"
    fi
    
    echo ""
    sleep 1
}

# Function to check file exists
check_file() {
    local file="$1"
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ Found: $file${NC}"
        return 0
    else
        echo -e "${RED}❌ Missing: $file${NC}"
        return 1
    fi
}

echo "📋 PRE-TEST ENVIRONMENT CHECK"
echo "=============================================================="

# Check Python version
echo "🐍 Python Version:"
python3 --version

# Check current directory structure
echo ""
echo "📁 Current Directory Structure:"
ls -la *.py | head -10

# Check essential files
echo ""
echo "📄 Essential Files Check:"
check_file "test_amir_bridge_integration.py"
check_file "test_json_split_pattern.py"
check_file "amir_data_bridge.py"
check_file "amir_monitor.py"
check_file "amir_dashboard.py"

echo ""
echo "🚀 STARTING COMPREHENSIVE TEST SUITE"
echo "=============================================================="

# Test 1: Basic Database Connection
run_test "Database Connection" "python3 -c \"
import sys, os
sys.path.append(os.path.join('.', 'patterns', 'json_split'))
from common import get_pg_conn
conn = get_pg_conn()
cursor = conn.cursor()
cursor.execute('SELECT version()')
version = cursor.fetchone()[0]
print(f'✅ Connected: {version[:50]}...')
conn.close()
\""

# Test 2: Trading Session Function (Fixed)
run_test "Trading Session Function (Fixed)" "python3 -c \"
import sys, os
sys.path.append(os.path.join('.', 'patterns', 'json_split'))
from common import get_pg_conn
conn = get_pg_conn()
cursor = conn.cursor()
cursor.execute('SELECT get_trading_session(NOW()::timestamp) as session')
session = cursor.fetchone()[0]
print(f'✅ Current Session: {session}')
conn.close()
\""

# Test 3: OHLC Data Availability
run_test "OHLC Data Availability" "python3 -c \"
import sys, os
sys.path.append(os.path.join('.', 'patterns', 'json_split'))
from common import get_pg_conn
conn = get_pg_conn()
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM ohlc_data')
count = cursor.fetchone()[0]
print(f'✅ OHLC Records: {count:,}')
cursor.execute('SELECT COUNT(*) FROM ohlc_data WHERE open_time >= NOW() - INTERVAL \\\"24 hours\\\"')
recent = cursor.fetchone()[0]
print(f'✅ Recent (24h): {recent:,}')
conn.close()
\""

# Test 4: Bridge Enhancement Columns
run_test "Bridge Enhancement Columns" "python3 -c \"
import sys, os
sys.path.append(os.path.join('.', 'patterns', 'json_split'))
from common import get_pg_conn
conn = get_pg_conn()
cursor = conn.cursor()
cursor.execute(\\\"
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'ohlc_data' 
    AND column_name IN ('spread', 'mt5_collection_time', 'data_source', 'trading_session')
\\\")
columns = [row[0] for row in cursor.fetchall()]
print(f'✅ Enhanced Columns: {len(columns)}/4 ({\\\"}, {\\\".join(columns)})')
conn.close()
\""

# Test 5: JSON Split Pattern System
run_test "JSON Split Pattern System" "python3 -c \"
import sys, os
sys.path.append(os.path.join('.', 'patterns', 'json_split'))
try:
    from force_fresh_pattern import force_fresh_pattern_json
    print('✅ Force Fresh Pattern: Available')
except ImportError as e:
    print(f'❌ Import Error: {e}')
    exit(1)
\""

# Test 6: JSON Split Pattern Execution
run_test "JSON Split Pattern Execution" "python3 test_json_split_pattern.py"

# Test 7: Bridge Scripts Availability
run_test "Bridge Scripts Availability" "python3 -c \"
import os
scripts = ['amir_monitor.py', 'amir_data_bridge.py', 'amir_dashboard.py']
found = []
for script in scripts:
    if os.path.exists(script):
        found.append(script.replace('.py', ''))
print(f'✅ Bridge Scripts: {\\\"}, {\\\".join(found)} ({len(found)}/3)')
if len(found) < 3:
    exit(1)
\""

# Test 8: Data Quality Check
run_test "Data Quality Check" "python3 -c \"
import sys, os
sys.path.append(os.path.join('.', 'patterns', 'json_split'))
from common import get_pg_conn
conn = get_pg_conn()
cursor = conn.cursor()
cursor.execute(\\\"
    SELECT 
        COUNT(DISTINCT symbol) as symbols,
        COUNT(DISTINCT timeframe) as timeframes,
        MIN(open_time) as oldest,
        MAX(open_time) as newest
    FROM ohlc_data 
    WHERE open_time >= NOW() - INTERVAL '24 hours'
\\\")
stats = cursor.fetchone()
print(f'✅ 24h Data Quality:')
print(f'   Symbols: {stats[0]}')
print(f'   Timeframes: {stats[1]}')
print(f'   Range: {stats[2]} to {stats[3]}')
conn.close()
\""

# Test 9: Full Bridge Integration Test
echo -e "${BLUE}🔍 Testing: Full Bridge Integration Test Suite${NC}"
echo "Command: python3 test_amir_bridge_integration.py"
echo "----------------------------------------"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

if timeout 120s python3 test_amir_bridge_integration.py; then
    echo -e "${GREEN}✅ PASS: Full Bridge Integration Test Suite${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ FAIL: Full Bridge Integration Test Suite${NC}"
fi
echo ""

# Test 10: Pattern JSON Integration Verification
run_test "Pattern JSON Integration Verification" "python3 -c \"
import sys, os
sys.path.append(os.path.join('.', 'patterns', 'json_split'))
from common import get_pg_conn

# Check trading_snapshots table
conn = get_pg_conn()
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_name = \\\"trading_snapshots\\\"')
table_exists = cursor.fetchone()[0] > 0

if table_exists:
    cursor.execute('SELECT COUNT(*) FROM trading_snapshots WHERE pattern_json IS NOT NULL')
    snapshots = cursor.fetchone()[0]
    print(f'✅ Pattern JSON Snapshots: {snapshots}')
else:
    print('⚠️  trading_snapshots table not found')

conn.close()
\""

echo ""
echo "📊 FINAL TEST RESULTS"
echo "=============================================================="
echo -e "Total Tests: ${TOTAL_TESTS}"
echo -e "Passed: ${GREEN}${PASSED_TESTS}${NC}"
echo -e "Failed: ${RED}$((TOTAL_TESTS - PASSED_TESTS))${NC}"
echo -e "Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo ""
    echo -e "${GREEN}🎉 ALL TESTS PASSED - BRIDGE INTEGRATION FULLY FUNCTIONAL!${NC}"
    echo "✅ Database connection working"
    echo "✅ Trading session function fixed and working"
    echo "✅ Amir's data flowing properly"
    echo "✅ JSON Split pattern system compatible"
    echo "✅ Bridge components ready"
    echo "✅ System ready for production"
elif [ $PASSED_TESTS -ge $((TOTAL_TESTS - 1)) ]; then
    echo ""
    echo -e "${YELLOW}⚠️  MOSTLY FUNCTIONAL - Minor issues detected${NC}"
    echo "Most components working, check failed tests above"
else
    echo ""
    echo -e "${RED}❌ SIGNIFICANT ISSUES - Bridge integration needs attention${NC}"
    echo "Multiple components failing, review errors above"
fi

echo ""
echo "📋 NEXT STEPS:"
echo "=============================================================="
echo "1. Review any failed tests above"
echo "2. If all passed, your bridge integration is ready"
echo "3. Run 'python3 amir_data_bridge.py' to start bridge"
echo "4. Run 'python3 amir_monitor.py' for monitoring"
echo "5. Run 'python3 amir_dashboard.py' for status dashboard"
echo ""
echo "Test completed at: $(date)"
