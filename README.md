# 🚀 Miando Trading Platform

Miando is a comprehensive trading platform featuring **Force-Fresh Pattern JSON integration**, SSL-secured PostgreSQL database, and advanced Python-based trading analytics with real-time technical indicator analysis.

## ⭐ L## 📖 Documentation

### 🔥 **NE## 🐛 Troubleshooting

### 🔥 **NEW: Pattern JSON Issues**
1. **Stale Data Problem**: Use `python3 pattern_json_live.py --force-fresh` for guaranteed current data
2. **Spread Calculation Issues**: Verify latest M1 data with `python3 check_fresh_data.py`
3. **Session Mapping Problems**: Check UTC hour mapping in trading session logic
4. **Validation Failures**: Run `python3 validate_pattern_json.py` for comprehensive diagnostics

### Common Issues
1. **SSL Connection Failed**: Ensure certificates are properly generated
2. **Bot Connection Issues**: Check database container is running
3. **Permission Denied**: Run `./fix_permissions.sh`
4. **Data Freshness**: Use force-fresh mode when critical accuracy is needed

### Performance Issues
```bash
# Quick performance tests
cd patterns/json_split/
bash run_super_fast_tests.sh    # ≤5 seconds
bash run_fast_tests.sh          # ≤10 seconds

# Force-fresh vs regular comparison
python3 test_force_fresh.py
```

### Logs
```bash
# Database logs
docker logs miando-db

# Bot logs
docker logs indikator-bot

# All services
docker-compose logs

# Pattern JSON validation logs
cd patterns/json_split/
python3 validate_pattern_json.py
```ent Reports**
- **[Force-Fresh Integration Report](DEV_REPORT_2025-08-09.md)** - Comprehensive development report for Pattern JSON enhancement
- **[Quick Development Summary](QUICK_SUMMARY_2025-08-09.md)** - Executive summary of latest features

### Pattern JSON Analytics
- **[Pattern JSON Validation](patterns/json_split/NOTES_VALIDATION.md)** - System validation against critical requirements
- **[Prediction Analysis](patterns/json_split/PREDICTION_ANALYSIS.md)** - 1-hour prediction system documentation
- **[Spread Analysis](patterns/json_split/SPREAD_ANALYSIS.md)** - Spread calculation methodology and testing
- **[Testing Guide](patterns/json_split/TESTING_GUIDE.md)** - Comprehensive testing instructions

### Professional Development & DevOps
- **[Dev-Test-Prod Environments](docs/DEV-TEST-PROD-ENVIRONMENTS.md)** - Enterprise-grade environment management setup
- **[Comprehensive Testing Approach](docs/COMPREHENSIVE_TESTING_APPROACH.md)** - Professional testing infrastructure documentation
- **[Testing Executive Summary](docs/TESTING_EXECUTIVE_SUMMARY.md)** - Executive overview of testing practices

### CI/CD & Automation
- **GitHub Actions**: Automated testing and deployment pipeline in `.github/workflows/ci-cd.yml`
- **Environment Management**: Professional dev/test/prod environment separation
- **Quality Assurance**: 80% test coverage requirement with comprehensive quality gateses (August 2025)

### 🔥 **NEW: Force-Fresh Pattern JSON System**
- **Real-time data guarantee**: Bypass caching for absolutely fresh market data
- **Enhanced spread calculation**: Live M1 candle-based spread computation
- **Command-line control**: `--force-fresh` flag for critical operations
- **Session accuracy**: Precise Sydney/London/New York session mapping
- **Data validation**: Comprehensive testing and monitoring suite

### 🚀 **Recent Enhancements**
- ✅ **Pattern JSON Live Export**: Optimized 152-candle data structure for vector matching
- ✅ **Session Timing Fix**: Corrected Hour 23 UTC mapping to Sydney session  
- ✅ **Spread Integration**: Real-time spread calculation from latest M1 data
- ✅ **1-Hour Predictions**: Max gain/loss forecasting system
- ✅ **CI/CD Pipeline**: Automated testing with GitHub Actions
- ✅ **Comprehensive Validation**: 5-point quality assurance system

## 🏗️ Architecture

This platform consists of multiple integrated services:
- **miando-db**: SSL-secured PostgreSQL database with trading schema
- **indikator-bot**: Python trading bot with technical indicator calculations  
- **patterns**: Advanced Pattern JSON analytics with force-fresh capabilities
- **json_exporter**: Real-time data export and validation systems

## 📋 Prerequisites

- Docker & Docker Compose
- SSL certificates (automatically generated if not present)

## 🚀 Quick Start

### 1. Generate SSL Certificates (if needed)
```bash
./generate_ssl.sh
```

### 2. Build and Run Services
```bash
docker-compose up --build
```

### 3. **NEW: Force-Fresh Pattern JSON** 🔥
```bash
# Navigate to patterns directory
cd patterns/json_split/

# Generate guaranteed fresh Pattern JSON
python3 pattern_json_live.py --force-fresh

# Quick data verification
python3 check_fresh_data.py

# Emergency fresh pattern generation
python3 force_fresh_pattern.py
```

### 4. Access Services
- **Database**: `localhost:5434` (SSL enabled)
- **Bot**: Runs automatically and connects to database
- **Pattern JSON**: Real-time trading pattern analysis

## 🔧 Configuration

### Database Configuration
- **Database**: `miando`
- **User**: `miando`
- **Password**: `changeme`
- **Port**: `5434` (mapped from container's 5432)
- **SSL**: Enabled with certificates

### Bot Configuration
The trading bot calculates various technical indicators:
- ADX (Average Directional Index)
- ATR (Average True Range)
- Bollinger Bands
- CCI (Commodity Channel Index)
- EMA (Exponential Moving Average)
- MACD (Moving Average Convergence Divergence)
- OBV (On-Balance Volume)
- RSI (Relative Strength Index)
- SMA (Simple Moving Average)
- Stochastic Oscillator
- Williams %R

## 📊 Database Schema

The database includes the following main tables:

### Core Trading Tables
- `accounts` - Trading account information
- `account_state` - Real-time account status and metrics
- `open_trades` - Currently active trading positions
- `closed_trades` - Historical trading records
- `planned_trades` - Strategy-generated trade plans

### Market Data Tables
- `ohlc_data` - OHLC price data with technical indicators
- `trading_snapshots` - **NEW**: Pattern JSON storage with real-time analytics

### 🔥 **NEW: Pattern JSON Features**
- **Force-Fresh Data**: Bypass caching for guaranteed current-day data
- **Optimized Structure**: 152-candle data optimized for vector matching
- **Real-time Spread**: Live calculation from latest M1 candles
- **Session Mapping**: Accurate Sydney/London/New York session detection
- **1-Hour Predictions**: Max gain/loss percentage forecasting
- **Comprehensive Validation**: 5-point quality assurance system

### Key Features
- **SSL Security**: All database connections encrypted
- **Technical Indicators**: Pre-calculated and stored
- **Trade Management**: Complete trade lifecycle tracking
- **Account Monitoring**: Real-time account state tracking
- **Pattern Analytics**: Advanced pattern recognition and prediction

## 🛠️ Development

### Project Structure
```
Miando/
├── docker-compose.yml          # Multi-service orchestration
├── Dockerfile                  # PostgreSQL with SSL
├── schema.sql                  # Database schema
├── enable_ssl.sh              # SSL configuration script
├── fix_permissions.sh         # Permission handling
├── generate_ssl.sh            # SSL certificate generation
├── server.crt                 # SSL certificate
├── server.key                 # SSL private key
├── patterns/                  # 🔥 NEW: Pattern JSON Analytics
│   └── json_split/           # Force-fresh pattern system
│       ├── pattern_json_live.py    # Main pattern generator (--force-fresh support)
│       ├── common.py               # Enhanced database functions
│       ├── force_fresh_pattern.py  # Emergency fresh generation
│       ├── check_fresh_data.py     # Quick verification
│       ├── test_force_fresh.py     # Testing suite
│       └── validate_pattern_json.py # Comprehensive validation
├── indikator_bot/
│   ├── Dockerfile             # Python bot container
│   ├── indikator_bot.py       # Trading bot logic
│   └── server.crt             # SSL certificate for bot
└── .github/workflows/         # 🔥 NEW: CI/CD Pipeline
    └── ci-cd.yml              # Automated testing and deployment
```

### Environment Variables
You can customize the following environment variables in `docker-compose.yml`:
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- `DB_HOST` - Database host for bot connection
- `DB_PORT` - Database port
- `DB_NAME` - Database name for bot
- `DB_USER` - Database user for bot
- `DB_PASSWORD` - Database password for bot

## 🔐 Security Features

- **SSL/TLS Encryption**: All database connections secured
- **Certificate Management**: Automated certificate handling
- **Permission Control**: Proper file permissions for SSL keys
- **Container Isolation**: Services run in isolated containers

## 📈 Usage Examples

### 🔥 **NEW: Force-Fresh Pattern JSON** 
```bash
# Regular pattern generation (faster, may use cached data)
cd patterns/json_split/
python3 pattern_json_live.py

# Force-fresh generation (guaranteed current data)
python3 pattern_json_live.py --force-fresh

# Emergency fresh pattern generation
python3 force_fresh_pattern.py

# Quick data verification
python3 check_fresh_data.py

# Comprehensive validation testing
python3 test_force_fresh.py
```

### **API Integration**
```python
from common import get_latest_m1_time
from pattern_json_live import build_pattern_json, calculate_spread_from_latest_m1

# Force fresh data retrieval
latest_time = get_latest_m1_time('XAUUSD', force_fresh=True)
spread = calculate_spread_from_latest_m1('XAUUSD', latest_time, force_fresh=True)
pattern_json = build_pattern_json('XAUUSD', force_fresh=True)
```

### Connect to Database
```bash
# Using psql with SSL
psql "postgresql://miando:changeme@localhost:5434/miando?sslmode=require"
```

### View Bot Logs
```bash
docker logs indikator-bot
```

### Database Backup
```bash
docker exec miando-db pg_dump -U miando miando > backup.sql
```

## 🔧 Maintenance

### 🔥 **NEW: Pattern JSON Monitoring**
```bash
# Force fresh data when needed
cd patterns/json_split/
python3 pattern_json_live.py --force-fresh

# Validate data freshness
python3 check_fresh_data.py

# Run comprehensive pattern validation
python3 validate_pattern_json.py

# Performance testing
bash run_super_fast_tests.sh
```

### Update Indicators
The bot automatically calculates and updates technical indicators every 30 seconds.

### SSL Certificate Renewal
```bash
./generate_ssl.sh
docker-compose restart
```

### Database Health Check
```bash
docker exec miando-db pg_isready -U miando
```

### **CI/CD Pipeline Status**
The project includes automated testing via GitHub Actions:
- **Code Quality**: Black formatting, Flake8 linting
- **Unit Tests**: Comprehensive test coverage with pytest
- **Integration Tests**: Database and service integration validation
- **Docker Tests**: Container environment verification
- **Performance Tests**: System performance benchmarking

## � Documentation

### Professional Development & DevOps
- **[Dev-Test-Prod Environments](docs/DEV-TEST-PROD-ENVIRONMENTS.md)** - Enterprise-grade environment management setup
- **[Comprehensive Testing Approach](docs/COMPREHENSIVE_TESTING_APPROACH.md)** - Professional testing infrastructure documentation
- **[Testing Executive Summary](docs/TESTING_EXECUTIVE_SUMMARY.md)** - Executive overview of testing practices

### CI/CD & Automation
- **GitHub Actions**: Automated testing and deployment pipeline in `.github/workflows/ci-cd.yml`
- **Environment Management**: Professional dev/test/prod environment separation
- **Quality Assurance**: 80% test coverage requirement with comprehensive quality gates

## �🐛 Troubleshooting

### Common Issues
1. **SSL Connection Failed**: Ensure certificates are properly generated
2. **Bot Connection Issues**: Check database container is running
3. **Permission Denied**: Run `./fix_permissions.sh`

### Logs
```bash
# Database logs
docker logs miando-db

# Bot logs
docker logs indikator-bot

# All services
docker-compose logs
```

## ⚡ Performance Benchmarks

### 🔥 **Force-Fresh Pattern JSON Performance**

**Regular Mode (Cached):**
- ⚡ **Execution Time**: ~2-3 seconds
- 📊 **Database Connections**: Pooled/cached
- 🔄 **Data Freshness**: May use cached data
- � **Memory Usage**: Low
- 🎯 **Use Case**: Frequent updates, development testing

**Force-Fresh Mode (Guaranteed Current):**
- ⚡ **Execution Time**: ~3-4 seconds (+1 second overhead)
- 📊 **Database Connections**: Fresh connection per operation
- 🔄 **Data Freshness**: ✅ Guaranteed current data
- 💾 **Memory Usage**: Slightly higher
- 🎯 **Use Case**: Critical trading decisions, real-time analysis

**Test Results Example:**
```
Before Force-Fresh: Spread = 0.27 (stale 2025-08-08 data)
After Force-Fresh:  Spread = 0.09 (fresh 2025-08-09 data)
Performance Cost:   +1 second for guaranteed accuracy
```

**Recommendation**: Use force-fresh for critical operations, regular mode for frequent monitoring.

## �📄 License

This project is proprietary software for Miando trading platform.

---
*For support and questions, please contact the development team.*

**🚀 Latest Update**: Force-Fresh Pattern JSON Integration (August 9, 2025) - Ensuring real-time trading accuracy with guaranteed fresh data!
