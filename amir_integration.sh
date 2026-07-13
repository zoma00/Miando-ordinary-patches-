#!/bin/bash
# 🚀 Amir Integration Startup Script
# Manages all components of Amir's MT5 data integration

echo "🌉 Miando - Amir Integration Manager"
echo "===================================="

# Function to show menu
show_menu() {
    echo ""
    echo "Select an option:"
    echo "1. 📊 Show Integration Dashboard"
    echo "2. 🔍 Quick Health Check"
    echo "3. 🌉 Start Data Bridge (Background)"
    echo "4. 📈 Start Continuous Monitoring"
    echo "5. 🧪 Test Pattern JSON Integration"
    echo "6. 📋 View Enhancement Spec for Amir"
    echo "7. 🛠️  Setup Database Schema"
    echo "8. 🚀 Start API Server"
    echo "9. 📊 Run Complete Integration Test"
    echo "0. ❌ Exit"
    echo ""
    read -p "Enter your choice [0-9]: " choice
}

# Function to run dashboard
run_dashboard() {
    echo "📊 Running Integration Dashboard..."
    python3 dashboard.py --status
}

# Function to run health check
run_health_check() {
    echo "🔍 Running Quick Health Check..."
    python3 monitor.py --check
}

# Function to start data bridge
start_bridge() {
    echo "🌉 Starting Data Bridge in background..."
    nohup python3 data_bridge.py > bridge.log 2>&1 &
    echo "✅ Bridge started! Check bridge.log for output"
    echo "🛑 To stop: pkill -f data_bridge.py"
}

# Function to start monitoring
start_monitoring() {
    echo "📈 Starting Continuous Monitoring..."
    echo "🛑 Press Ctrl+C to stop"
    python3 monitor.py --monitor
}

# Function to test Pattern JSON
test_pattern_json() {
    echo "🧪 Testing Pattern JSON Integration..."
    python3 dashboard.py --test
}

# Function to view enhancement spec
view_enhancement_spec() {
    echo "📋 Enhancement Specification for Amir:"
    echo "======================================"
    cat AMIR_ENHANCEMENT_SPEC.md | head -50
    echo ""
    echo "📄 Full specification available in: AMIR_ENHANCEMENT_SPEC.md"
}

# Function to setup database
setup_database() {
    echo "🛠️  Setting up Database Schema..."
    
    # Check if database is accessible
    if psql -h localhost -p 5434 -U miando -d miando -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ Database connection successful"
        
        # Add monitoring table
        psql -h localhost -p 5434 -U miando -d miando -c "
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
            );
            
            -- Add columns to ohlc_data for Amir integration
            ALTER TABLE ohlc_data ADD COLUMN IF NOT EXISTS spread DECIMAL(10,6) DEFAULT 0;
            ALTER TABLE ohlc_data ADD COLUMN IF NOT EXISTS mt5_collection_time TIMESTAMP;
            ALTER TABLE ohlc_data ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'unknown';
            ALTER TABLE ohlc_data ADD COLUMN IF NOT EXISTS trading_session VARCHAR(20);
            
            -- Create index for performance
            CREATE INDEX IF NOT EXISTS idx_ohlc_data_symbol_time ON ohlc_data(symbol, open_time DESC);
        " 2>/dev/null
        
        echo "✅ Database schema updated for Amir integration"
    else
        echo "❌ Cannot connect to database. Check connection settings."
    fi
}

# Function to start API server
start_api_server() {
    echo "🚀 Starting API Server..."
    echo "🛑 Press Ctrl+C to stop"
    python3 miando_data_api.py
}

# Function to run complete test
run_complete_test() {
    echo "📊 Running Complete Integration Test..."
    python3 test_mql5_integration.py
}

# Main menu loop
while true; do
    show_menu
    
    case $choice in
        1)
            run_dashboard
            ;;
        2)
            run_health_check
            ;;
        3)
            start_bridge
            ;;
        4)
            start_monitoring
            ;;
        5)
            test_pattern_json
            ;;
        6)
            view_enhancement_spec
            ;;
        7)
            setup_database
            ;;
        8)
            start_api_server
            ;;
        9)
            run_complete_test
            ;;
        0)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option. Please try again."
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
done
