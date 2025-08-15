"""
Unit tests for common utilities in the JSON split system.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import psycopg2
import json

# Clean imports using proper Python path
from patterns.json_split.common import (
    get_cursor, insert_snapshot, get_latest_m1_time, get_latest_account_id,
    format_timestamp_utc, safe_float, safe_int, log_info, log_error, log_success
)


class TestDatabaseUtils:
    """Test database utility functions."""
    
    def test_safe_float_with_valid_input(self):
        """Test safe_float with valid numeric input."""
        assert safe_float(42.5) == 42.5
        assert safe_float("42.5") == 42.5
        assert safe_float(42) == 42.0
        
    def test_safe_float_with_invalid_input(self):
        """Test safe_float with invalid input."""
        assert safe_float(None) == 0.0
        assert safe_float("invalid") == 0.0
        assert safe_float("") == 0.0
        
    def test_safe_int_with_valid_input(self):
        """Test safe_int with valid numeric input."""
        assert safe_int(42) == 42
        assert safe_int("42") == 42
        assert safe_int(42.7) == 42
        
    def test_safe_int_with_invalid_input(self):
        """Test safe_int with invalid input."""
        assert safe_int(None) == 0
        assert safe_int("invalid") == 0
        assert safe_int("") == 0
        
    def test_format_timestamp_utc(self):
        """Test UTC timestamp formatting."""
        dt = datetime(2025, 8, 8, 10, 30, 45, tzinfo=timezone.utc)
        result = format_timestamp_utc(dt)
        assert result == "2025-08-08T10:30:45+00:00"
        
    def test_format_timestamp_utc_with_none(self):
        """Test UTC timestamp formatting with None input."""
        result = format_timestamp_utc(None)
        assert result is None


@pytest.mark.database
class TestDatabaseConnections:
    """Test database connection functions."""
    
    @patch('common.psycopg2.connect')
    def test_get_cursor_success(self, mock_connect):
        """Test successful database cursor creation."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        with get_cursor() as cursor:
            assert cursor is not None
            
        mock_conn.cursor.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
        
    @patch('common.psycopg2.connect')
    def test_get_cursor_with_dict_cursor(self, mock_connect):
        """Test database cursor creation with dict cursor."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        with get_cursor(dict_cursor=True) as cursor:
            assert cursor is not None
            
        # Check that RealDictCursor was requested
        mock_conn.cursor.assert_called_once()
        
    @patch('common.psycopg2.connect')
    def test_get_cursor_connection_failure(self, mock_connect):
        """Test database cursor creation with connection failure."""
        mock_connect.side_effect = psycopg2.OperationalError("Connection failed")
        
        with pytest.raises(psycopg2.OperationalError):
            with get_cursor() as cursor:
                pass


@pytest.mark.database
class TestSnapshotOperations:
    """Test snapshot insertion operations."""
    
    @patch('common.get_cursor')
    def test_insert_snapshot_success(self, mock_get_cursor):
        """Test successful snapshot insertion."""
        mock_cursor = MagicMock()
        mock_get_cursor.return_value.__enter__.return_value = mock_cursor
        
        test_data = {"test": "data", "value": 123}
        
        result = insert_snapshot(
            symbol="EURUSD",
            snapshot_time=datetime(2025, 8, 8, 10, 0, 0, tzinfo=timezone.utc),
            json_column_name="test_json",
            json_data=test_data
        )
        
        assert result is True
        mock_cursor.execute.assert_called()
        
    @patch('common.get_cursor')
    def test_insert_snapshot_database_error(self, mock_get_cursor):
        """Test snapshot insertion with database error."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = psycopg2.Error("Database error")
        mock_get_cursor.return_value.__enter__.return_value = mock_cursor
        
        test_data = {"test": "data"}
        
        result = insert_snapshot(
            symbol="EURUSD",
            snapshot_time=datetime(2025, 8, 8, 10, 0, 0, tzinfo=timezone.utc),
            json_column_name="test_json",
            json_data=test_data
        )
        
        assert result is False


@pytest.mark.database
class TestDataRetrieval:
    """Test data retrieval functions."""
    
    @patch('common.get_cursor')
    def test_get_latest_m1_time_success(self, mock_get_cursor):
        """Test successful M1 time retrieval."""
        mock_cursor = MagicMock()
        test_time = datetime(2025, 8, 8, 10, 0, 0, tzinfo=timezone.utc)
        mock_cursor.fetchone.return_value = [test_time]
        mock_get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = get_latest_m1_time("EURUSD")
        
        assert result == test_time
        mock_cursor.execute.assert_called_once()
        
    @patch('common.get_cursor')
    def test_get_latest_m1_time_no_data(self, mock_get_cursor):
        """Test M1 time retrieval with no data."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = get_latest_m1_time("EURUSD")
        
        assert result is None
        
    @patch('common.get_cursor')
    def test_get_latest_account_id_success(self, mock_get_cursor):
        """Test successful account ID retrieval."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ["12345"]
        mock_get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = get_latest_account_id()
        
        assert result == "12345"
        mock_cursor.execute.assert_called_once()
        
    @patch('common.get_cursor')
    def test_get_latest_account_id_no_data(self, mock_get_cursor):
        """Test account ID retrieval with no data."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = get_latest_account_id()
        
        assert result is None


class TestLoggingFunctions:
    """Test logging utility functions."""
    
    @patch('common.print')
    def test_log_info(self, mock_print):
        """Test info logging."""
        log_info("Test message")
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        assert "INFO" in args
        assert "Test message" in args
        
    @patch('common.print')
    def test_log_error(self, mock_print):
        """Test error logging."""
        log_error("Error message")
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        assert "ERROR" in args
        assert "Error message" in args
        
    @patch('common.print')
    def test_log_success(self, mock_print):
        """Test success logging."""
        log_success("Success message")
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        assert "SUCCESS" in args
        assert "Success message" in args
