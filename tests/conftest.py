"""
Test configuration and fixtures for Miando trading system tests.
"""
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timezone
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, patch
import tempfile
import shutil

# Import from your modules
import sys
sys.path.append('/home/hazem/Miando/patterns/json_split')

from common import get_cursor, DB_CONFIG


@pytest.fixture(scope="session")
def test_db_config() -> Dict[str, str]:
    """Test database configuration."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5434"),
        "database": "miando_test",
        "user": os.getenv("DB_USER", "miando"),
        "password": os.getenv("DB_PASSWORD", "changeme"),
        "sslmode": "disable"  # Disable SSL for testing
    }


@pytest.fixture(scope="session")
def test_db_connection(test_db_config):
    """Create test database connection."""
    try:
        # Try to create test database
        admin_config = test_db_config.copy()
        admin_config["database"] = "miando"  # Connect to main DB first
        
        conn = psycopg2.connect(**admin_config)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Create test database if it doesn't exist
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'miando_test'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE miando_test")
        
        conn.close()
        
        # Connect to test database
        test_conn = psycopg2.connect(**test_db_config)
        yield test_conn
        
    except Exception as e:
        pytest.skip(f"Could not create test database: {e}")
    finally:
        if 'test_conn' in locals():
            test_conn.close()


@pytest.fixture
def db_cursor(test_db_connection):
    """Database cursor for tests."""
    with test_db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        yield cur
        test_db_connection.rollback()


@pytest.fixture
def mock_db_config(test_db_config):
    """Mock database configuration for testing."""
    with patch('common.DB_CONFIG', test_db_config):
        yield test_db_config


@pytest.fixture
def sample_ohlc_data():
    """Sample OHLC data for testing."""
    return {
        "M1": [
            {
                "open_time": "2025-08-08T10:00:00+00:00",
                "open": 1.0950,
                "high": 1.0960,
                "low": 1.0940,
                "close": 1.0955,
                "volume": 1000,
                "adx": 25.5,
                "atr": 0.0015,
                "rsi": 55.2
            }
        ],
        "M5": [
            {
                "open_time": "2025-08-08T10:00:00+00:00",
                "open": 1.0950,
                "high": 1.0970,
                "low": 1.0930,
                "close": 1.0955,
                "volume": 5000,
                "adx": 28.1,
                "atr": 0.0025,
                "rsi": 58.7
            }
        ]
    }


@pytest.fixture
def sample_account_state():
    """Sample account state data for testing."""
    return {
        "timestamp": "2025-08-08T10:00:00+00:00",
        "balance": 10000.0,
        "equity": 10150.0,
        "margin": 500.0,
        "free_margin": 9650.0,
        "leverage": 100,
        "profit": 150.0,
        "currency": "USD"
    }


@pytest.fixture
def sample_trades():
    """Sample trade data for testing."""
    return [
        {
            "symbol": "EURUSD",
            "magic": 12345,
            "order_type": "buy",
            "lot_size": 0.1,
            "open_price": 1.0950,
            "sl": 1.0900,
            "tp": 1.1000,
            "profit": 50.0,
            "open_time": "2025-08-08T09:00:00+00:00",
            "status": "open"
        }
    ]


@pytest.fixture
def temp_log_dir():
    """Temporary directory for log files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    mock_dt = datetime(2025, 8, 8, 10, 0, 0, tzinfo=timezone.utc)
    with patch('common.datetime') as mock:
        mock.now.return_value = mock_dt
        mock.utcnow.return_value = mock_dt
        yield mock_dt


@pytest.fixture(autouse=True)
def cleanup_database_state(test_db_connection):
    """Ensure clean database state for each test."""
    yield
    # Cleanup after each test
    try:
        with test_db_connection.cursor() as cur:
            # Clean up test data
            cur.execute("DELETE FROM trading_snapshots WHERE symbol LIKE 'TEST_%'")
            test_db_connection.commit()
    except Exception:
        test_db_connection.rollback()


class MockExporter:
    """Mock exporter for testing."""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.call_count = 0
        
    def export(self):
        self.call_count += 1
        if self.should_fail:
            raise Exception("Mock export failure")
        return True


# Performance testing fixtures
@pytest.fixture
def benchmark_config():
    """Configuration for benchmark tests."""
    return {
        'min_rounds': 5,
        'max_time': 10.0,
        'warmup': True,
        'warmup_iterations': 2
    }
