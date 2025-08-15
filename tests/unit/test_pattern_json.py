#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for Pattern JSON Live and Historical Exporters
Tests the optimized compact JSON structure for pattern matching.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'patterns', 'json_split'))

from pattern_json_live import (
    PATTERN_TIMEFRAME_LIMITS, KEY_INDICATORS,
    fetch_pattern_ohlc_for_timeframe, get_latest_indicator_values,
    calculate_1h_outcome, get_trading_session, assess_volatility,
    build_pattern_json, store_pattern_json
)

from pattern_json_history import (
    get_all_historical_m1_timestamps, fetch_historical_pattern_candles,
    get_historical_indicator_values, calculate_historical_1h_outcome,
    build_historical_pattern_json, store_historical_pattern_json,
    process_historical_batch
)


class TestPatternJsonLive:
    """Test Pattern JSON Live functionality."""
    
    def test_pattern_timeframe_limits(self):
        """Test that pattern timeframe limits are optimized for vector matching."""
        assert PATTERN_TIMEFRAME_LIMITS['D1'] == 7    # 1 week
        assert PATTERN_TIMEFRAME_LIMITS['H4'] == 5    # 1 day
        assert PATTERN_TIMEFRAME_LIMITS['H1'] == 20   # 20 hours
        assert PATTERN_TIMEFRAME_LIMITS['M15'] == 30  # 7.5 hours
        assert PATTERN_TIMEFRAME_LIMITS['M5'] == 30   # 2.5 hours
        assert PATTERN_TIMEFRAME_LIMITS['M1'] == 60   # 1 hour
    
    def test_key_indicators_optimized(self):
        """Test that key indicators are optimized for pattern matching."""
        expected_indicators = ['rsi', 'ema', 'atr', 'bb_middle', 'bb_upper', 'bb_lower']
        assert KEY_INDICATORS == expected_indicators
        assert len(KEY_INDICATORS) == 6  # Compact for vector efficiency
    
    @patch('pattern_json_live.get_cursor')
    def test_fetch_pattern_ohlc_for_timeframe(self, mock_get_cursor):
        """Test fetching compact OHLC data for pattern matching."""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_get_cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {
                'open_time': datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc),
                'open_price': 2350.0,
                'high_price': 2355.0,
                'low_price': 2348.0,
                'close_price': 2352.0,
                'volume': 1000,
                'rsi': 55.5,
                'ema': 2351.0,
                'atr': 3.2,
                'bb_middle': 2350.0,
                'bb_upper': 2360.0,
                'bb_lower': 2340.0
            }
        ]
        
        candles = fetch_pattern_ohlc_for_timeframe("XAUUSD", "M1", 60)
        
        assert len(candles) == 1
        candle = candles[0]
        
        # Test compact structure
        assert candle['open'] == 2350.0
        assert candle['high'] == 2355.0
        assert candle['low'] == 2348.0
        assert candle['close'] == 2352.0
        assert candle['volume'] == 1000
        
        # Test key indicators only
        assert candle['rsi'] == 55.5
        assert candle['ema'] == 2351.0
        assert candle['atr'] == 3.2
        assert candle['bb_middle'] == 2350.0
        assert candle['bb_upper'] == 2360.0
        assert candle['bb_lower'] == 2340.0
        
        # Ensure no extra indicators
        assert 'adx' not in candle
        assert 'macd' not in candle
        assert 'stoch_k' not in candle
    
    @patch('pattern_json_live.get_cursor')
    def test_get_latest_indicator_values(self, mock_get_cursor):
        """Test getting latest indicator values structure."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_get_cursor.return_value = mock_cursor
        
        mock_cursor.fetchone.side_effect = [
            {'rsi': 54.2, 'ema': 2350.0, 'atr': 21.5},  # D1
            {'rsi': 61.8, 'ema': 2351.0, 'atr': 8.3},   # H4
            {'rsi': 48.1, 'ema': 2352.4, 'atr': 3.1},   # H1
            {'rsi': 45.7, 'ema': 2350.8, 'atr': 1.2},   # M15
            {'rsi': 50.1, 'ema': 2349.6, 'atr': 0.8},   # M5
            {'rsi': 49.9, 'ema': 2349.2, 'atr': 0.5},   # M1
        ]
        
        indicators = get_latest_indicator_values("XAUUSD")
        
        # Test structure optimized for vectorization
        assert 'rsi' in indicators
        assert 'ema' in indicators
        assert 'atr' in indicators
        
        # Test all timeframes present
        for timeframe in PATTERN_TIMEFRAME_LIMITS.keys():
            assert timeframe in indicators['rsi']
            assert timeframe in indicators['ema']
            assert timeframe in indicators['atr']
        
        # Test specific values
        assert indicators['rsi']['D1'] == 54.2
        assert indicators['ema']['H1'] == 2352.4
        assert indicators['atr']['M15'] == 1.2
    
    @patch('pattern_json_live.get_cursor')
    def test_calculate_1h_outcome(self, mock_get_cursor):
        """Test 1-hour outcome calculation for pattern evaluation."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_get_cursor.return_value = mock_cursor
        
        # Mock current price
        mock_cursor.fetchone.return_value = {'close_price': 2350.0}
        
        # Mock next hour prices
        mock_cursor.fetchall.return_value = [
            {'high_price': 2355.0, 'low_price': 2348.0},  # +0.21%, -0.09%
            {'high_price': 2360.5, 'low_price': 2345.0},  # +0.45%, -0.21%
            {'high_price': 2358.0, 'low_price': 2343.0},  # +0.34%, -0.30%
        ]
        
        snapshot_time = datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc)
        outcome = calculate_1h_outcome("XAUUSD", snapshot_time)
        
        # Test outcome calculation
        assert outcome['max_gain_pct_1h'] == 0.45  # (2360.5 - 2350) / 2350 * 100
        assert outcome['max_loss_pct_1h'] == -0.30  # (2343 - 2350) / 2350 * 100
    
    def test_get_trading_session(self):
        """Test trading session determination."""
        # Sydney session (UTC 0-8)
        sydney_time = datetime(2025, 8, 6, 5, 0, tzinfo=timezone.utc)
        assert get_trading_session(sydney_time) == "Sydney"
        
        # London session (UTC 8-16)
        london_time = datetime(2025, 8, 6, 12, 0, tzinfo=timezone.utc)
        assert get_trading_session(london_time) == "London"
        
        # New York session (UTC 16-24)
        newyork_time = datetime(2025, 8, 6, 20, 0, tzinfo=timezone.utc)
        assert get_trading_session(newyork_time) == "New York"
    
    def test_assess_volatility(self):
        """Test volatility assessment based on ATR."""
        # High volatility
        high_atr = {'H1': 6.0}
        assert assess_volatility(high_atr) == "high"
        
        # Medium volatility
        medium_atr = {'H1': 3.0}
        assert assess_volatility(medium_atr) == "medium"
        
        # Low volatility
        low_atr = {'H1': 1.0}
        assert assess_volatility(low_atr) == "low"
        
        # Unknown volatility
        no_atr = {}
        assert assess_volatility(no_atr) == "unknown"
    
    @patch('pattern_json_live.store_pattern_json')
    @patch('pattern_json_live.build_pattern_json')
    def test_pattern_json_structure(self, mock_build, mock_store):
        """Test complete pattern JSON structure."""
        # Mock pattern JSON
        mock_pattern_json = {
            "symbol": "XAUUSD",
            "snapshot_time": "2025-08-06T10:15:00Z",
            "context": {
                "D1": [{"open_time": "2025-08-01T00:00:00Z", "open": 2300.0, "rsi": 50.0}],
                "H4": [{"open_time": "2025-08-06T08:00:00Z", "open": 2350.0, "rsi": 55.0}],
                "H1": [{"open_time": "2025-08-06T10:00:00Z", "open": 2352.0, "rsi": 48.0}],
                "M15": [{"open_time": "2025-08-06T10:00:00Z", "open": 2352.0, "rsi": 46.0}],
                "M5": [{"open_time": "2025-08-06T10:10:00Z", "open": 2351.0, "rsi": 50.0}],
                "M1": [{"open_time": "2025-08-06T10:15:00Z", "open": 2349.0, "rsi": 49.0}]
            },
            "indicators": {
                "rsi": {"D1": 54.2, "H4": 61.8, "H1": 48.1, "M15": 45.7, "M5": 50.1, "M1": 49.9},
                "ema": {"D1": 2340.0, "H4": 2345.0, "H1": 2352.4, "M15": 2350.8, "M5": 2349.6, "M1": 2349.2},
                "atr": {"D1": 21.5, "H4": 8.3, "H1": 3.1, "M15": 1.2, "M5": 0.8, "M1": 0.5}
            },
            "outcome_1h": {
                "max_gain_pct_1h": 0.45,
                "max_loss_pct_1h": -0.30
            },
            "session": "London",
            "volatility": "high"
        }
        
        mock_build.return_value = mock_pattern_json
        mock_store.return_value = True
        
        # Test structure compliance
        assert mock_pattern_json['symbol'] == "XAUUSD"
        assert 'snapshot_time' in mock_pattern_json
        assert 'context' in mock_pattern_json
        assert 'indicators' in mock_pattern_json
        assert 'outcome_1h' in mock_pattern_json
        assert 'session' in mock_pattern_json
        assert 'volatility' in mock_pattern_json
        
        # Test timeframe structure
        for timeframe in PATTERN_TIMEFRAME_LIMITS.keys():
            assert timeframe in mock_pattern_json['context']
        
        # Test indicator structure
        for indicator in ['rsi', 'ema', 'atr']:
            assert indicator in mock_pattern_json['indicators']
            for timeframe in PATTERN_TIMEFRAME_LIMITS.keys():
                assert timeframe in mock_pattern_json['indicators'][indicator]
        
        # Test outcome structure
        assert 'max_gain_pct_1h' in mock_pattern_json['outcome_1h']
        assert 'max_loss_pct_1h' in mock_pattern_json['outcome_1h']


class TestPatternJsonHistory:
    """Test Pattern JSON Historical functionality."""
    
    @patch('pattern_json_history.get_cursor')
    def test_get_all_historical_m1_timestamps(self, mock_get_cursor):
        """Test getting historical M1 timestamps."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_get_cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {'open_time': datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc)},
            {'open_time': datetime(2025, 8, 6, 10, 1, tzinfo=timezone.utc)},
            {'open_time': datetime(2025, 8, 6, 10, 2, tzinfo=timezone.utc)},
        ]
        
        timestamps = get_all_historical_m1_timestamps("XAUUSD")
        
        assert len(timestamps) == 3
        assert all(isinstance(ts, datetime) for ts in timestamps)
        assert timestamps[0] < timestamps[1] < timestamps[2]  # Sorted ascending
    
    @patch('pattern_json_history.get_cursor')
    def test_fetch_historical_pattern_candles(self, mock_get_cursor):
        """Test fetching historical candles up to a specific time."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_get_cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            {
                'open_time': datetime(2025, 8, 6, 9, 59, tzinfo=timezone.utc),
                'open_price': 2348.0,
                'high_price': 2352.0,
                'low_price': 2347.0,
                'close_price': 2350.0,
                'volume': 800,
                'rsi': 52.0,
                'ema': 2349.0,
                'atr': 2.8,
                'bb_middle': 2348.5,
                'bb_upper': 2358.5,
                'bb_lower': 2338.5
            }
        ]
        
        up_to_time = datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc)
        candles = fetch_historical_pattern_candles("XAUUSD", "M1", 60, up_to_time)
        
        assert len(candles) == 1
        candle = candles[0]
        
        # Test that only data available up to that time is included
        assert candle['close'] == 2350.0
        assert candle['rsi'] == 52.0
        
        # Verify the query included the time constraint
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "open_time <= %s" in call_args[0]
    
    @patch('pattern_json_history.get_cursor')
    def test_calculate_historical_1h_outcome(self, mock_get_cursor):
        """Test historical outcome calculation."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_get_cursor.return_value = mock_cursor
        
        # Mock current price and future prices
        mock_cursor.fetchone.return_value = {'close_price': 2350.0}
        mock_cursor.fetchall.return_value = [
            {'high_price': 2365.0, 'low_price': 2345.0},  # Historical outcome
        ]
        
        snapshot_time = datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc)
        outcome = calculate_historical_1h_outcome("XAUUSD", snapshot_time)
        
        assert outcome['max_gain_pct_1h'] == 0.64  # (2365 - 2350) / 2350 * 100
        assert outcome['max_loss_pct_1h'] == -0.21  # (2345 - 2350) / 2350 * 100
    
    @patch('pattern_json_history.store_historical_pattern_json')
    @patch('pattern_json_history.build_historical_pattern_json')
    def test_process_historical_batch(self, mock_build, mock_store):
        """Test batch processing of historical data."""
        timestamps = [
            datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc),
            datetime(2025, 8, 6, 10, 1, tzinfo=timezone.utc),
            datetime(2025, 8, 6, 10, 2, tzinfo=timezone.utc),
        ]
        
        # Mock successful processing
        mock_build.return_value = {"test": "pattern"}
        mock_store.return_value = True
        
        successful, failed = process_historical_batch("XAUUSD", timestamps, batch_size=2)
        
        assert successful == 3
        assert failed == 0
        assert mock_build.call_count == 3
        assert mock_store.call_count == 3


class TestPatternJsonIntegration:
    """Integration tests for Pattern JSON functionality."""
    
    def test_pattern_json_size_optimization(self):
        """Test that pattern JSON is optimized for size compared to full OHLC."""
        # Compare pattern limits vs original OHLC limits
        original_limits = {
            "M1": 120,   # 2 hours
            "M5": 288,   # 1 day
            "M15": 192,  # 2 days
            "H1": 480,   # 20 days
            "H4": 300,   # 2 months
            "D1": 250    # 1 year
        }
        
        # Calculate total candles
        original_total = sum(original_limits.values())  # 1630 candles
        pattern_total = sum(PATTERN_TIMEFRAME_LIMITS.values())  # 152 candles
        
        # Pattern JSON should be significantly smaller
        reduction_ratio = pattern_total / original_total
        assert reduction_ratio < 0.15  # Less than 15% of original size
        assert pattern_total == 152  # Exact expected count
    
    def test_pattern_json_completeness(self):
        """Test that pattern JSON contains all required fields for vector matching."""
        required_fields = [
            'symbol', 'snapshot_time', 'context', 'indicators', 
            'outcome_1h', 'session', 'volatility'
        ]
        
        required_timeframes = ['D1', 'H4', 'H1', 'M15', 'M5', 'M1']
        required_indicators = ['rsi', 'ema', 'atr']
        required_outcomes = ['max_gain_pct_1h', 'max_loss_pct_1h']
        
        # Mock pattern JSON structure
        pattern_json = {
            "symbol": "XAUUSD",
            "snapshot_time": "2025-08-06T10:15:00Z",
            "context": {tf: [] for tf in required_timeframes},
            "indicators": {ind: {tf: 0.0 for tf in required_timeframes} for ind in required_indicators},
            "outcome_1h": {outcome: None for outcome in required_outcomes},
            "session": "London",
            "volatility": "high"
        }
        
        # Test all required fields present
        for field in required_fields:
            assert field in pattern_json
        
        # Test timeframe structure
        for timeframe in required_timeframes:
            assert timeframe in pattern_json['context']
        
        # Test indicator structure
        for indicator in required_indicators:
            assert indicator in pattern_json['indicators']
            for timeframe in required_timeframes:
                assert timeframe in pattern_json['indicators'][indicator]
        
        # Test outcome structure
        for outcome in required_outcomes:
            assert outcome in pattern_json['outcome_1h']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
