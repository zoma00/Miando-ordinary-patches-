#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for Pattern JSON Live and Historical Exporters
Tests the complete workflow with database integration.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Import modules to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'patterns', 'json_split'))

from pattern_json_live import main as live_main
from pattern_json_history import main as history_main


@pytest.mark.integration
class TestPatternJsonIntegration:
    """Integration tests for Pattern JSON functionality."""
    
    @pytest.fixture
    def setup_test_data(self):
        """Setup test data in database."""
        from common import get_cursor
        
        test_symbol = "XAUUSD"
        base_time = datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc)
        
        # Insert test OHLC data
        with get_cursor() as cur:
            # Clean existing test data
            cur.execute("DELETE FROM ohlc_data WHERE symbol = %s", (test_symbol,))
            cur.execute("DELETE FROM trading_snapshots WHERE symbol = %s", (test_symbol,))
            
            # Insert test data for multiple timeframes
            timeframes = ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']
            
            for i, timeframe in enumerate(timeframes):
                for j in range(100):  # Enough data for pattern limits
                    time_offset = timedelta(minutes=j) if timeframe == 'M1' else timedelta(hours=j)
                    open_time = base_time - time_offset
                    
                    cur.execute("""
                        INSERT INTO ohlc_data (
                            symbol, timeframe, open_time,
                            open_price, high_price, low_price, close_price, volume,
                            rsi, ema, atr, bb_middle, bb_upper, bb_lower
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        test_symbol, timeframe, open_time,
                        2350.0 + i, 2355.0 + i, 2348.0 + i, 2352.0 + i, 1000,
                        50.0 + i, 2351.0 + i, 3.0 + i, 2350.0 + i, 2360.0 + i, 2340.0 + i
                    ))
        
        yield test_symbol
        
        # Cleanup
        with get_cursor() as cur:
            cur.execute("DELETE FROM ohlc_data WHERE symbol = %s", (test_symbol,))
            cur.execute("DELETE FROM trading_snapshots WHERE symbol = %s", (test_symbol,))
    
    def test_pattern_json_live_integration(self, setup_test_data):
        """Test complete live pattern JSON workflow."""
        from common import get_cursor, SYMBOL
        from pattern_json_live import build_pattern_json, store_pattern_json
        
        # Build pattern JSON
        pattern_json = build_pattern_json(SYMBOL)
        
        assert pattern_json is not None
        assert pattern_json['symbol'] == SYMBOL
        assert 'snapshot_time' in pattern_json
        assert 'context' in pattern_json
        assert 'indicators' in pattern_json
        assert 'outcome_1h' in pattern_json
        
        # Test compact structure
        context = pattern_json['context']
        assert len(context['M1']) <= 60    # 1 hour
        assert len(context['M5']) <= 30    # 2.5 hours
        assert len(context['M15']) <= 30   # 7.5 hours
        assert len(context['H1']) <= 20    # 20 hours
        assert len(context['H4']) <= 5     # 1 day
        assert len(context['D1']) <= 7     # 1 week
        
        # Test indicators structure
        indicators = pattern_json['indicators']
        assert 'rsi' in indicators
        assert 'ema' in indicators
        assert 'atr' in indicators
        
        # Store in database
        snapshot_time = datetime.fromisoformat(pattern_json["snapshot_time"].replace('Z', '+00:00'))
        success = store_pattern_json(SYMBOL, snapshot_time, pattern_json)
        assert success is True
        
        # Verify stored in database
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT pattern_json
                FROM trading_snapshots
                WHERE symbol = %s AND snapshot_time = %s
            """, (SYMBOL, snapshot_time))
            
            row = cur.fetchone()
            assert row is not None
            stored_json = row['pattern_json']
            
            # Verify structure
            assert stored_json['symbol'] == SYMBOL
            assert 'context' in stored_json
            assert 'indicators' in stored_json
    
    def test_pattern_json_historical_integration(self, setup_test_data):
        """Test complete historical pattern JSON workflow."""
        from common import get_cursor, SYMBOL
        from pattern_json_history import (
            get_all_historical_m1_timestamps,
            build_historical_pattern_json,
            store_historical_pattern_json
        )
        
        # Get historical timestamps
        start_date = datetime(2025, 8, 6, 9, 50, tzinfo=timezone.utc)
        end_date = datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc)
        timestamps = get_all_historical_m1_timestamps(SYMBOL, start_date, end_date)
        
        assert len(timestamps) > 0
        
        # Test historical pattern JSON generation
        test_timestamp = timestamps[0] if timestamps else start_date
        historical_json = build_historical_pattern_json(SYMBOL, test_timestamp)
        
        assert historical_json is not None
        assert historical_json['symbol'] == SYMBOL
        assert 'snapshot_time' in historical_json
        assert 'context' in historical_json
        assert 'outcome_1h' in historical_json
        
        # Store historical pattern JSON
        success = store_historical_pattern_json(SYMBOL, test_timestamp, historical_json)
        assert success is True
        
        # Verify in database
        with get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT pattern_json
                FROM trading_snapshots
                WHERE symbol = %s AND snapshot_time = %s
            """, (SYMBOL, test_timestamp))
            
            row = cur.fetchone()
            assert row is not None
            assert row['pattern_json']['symbol'] == SYMBOL
    
    def test_pattern_json_outcome_calculation(self, setup_test_data):
        """Test 1-hour outcome calculation accuracy."""
        from common import get_cursor, SYMBOL
        from pattern_json_live import calculate_1h_outcome
        
        # Setup specific test data for outcome calculation
        base_time = datetime(2025, 8, 6, 10, 0, tzinfo=timezone.utc)
        
        with get_cursor() as cur:
            # Insert current price
            cur.execute("""
                INSERT INTO ohlc_data (
                    symbol, timeframe, open_time, close_price
                ) VALUES (%s, 'M1', %s, %s)
                ON CONFLICT (symbol, timeframe, open_time) 
                DO UPDATE SET close_price = EXCLUDED.close_price
            """, (SYMBOL, base_time, 2350.0))
            
            # Insert future prices for next hour
            for i in range(1, 61):  # 60 minutes
                future_time = base_time + timedelta(minutes=i)
                high_price = 2350.0 + (i * 0.2)  # Gradual increase
                low_price = 2350.0 - (i * 0.1)   # Gradual decrease
                
                cur.execute("""
                    INSERT INTO ohlc_data (
                        symbol, timeframe, open_time, high_price, low_price
                    ) VALUES (%s, 'M1', %s, %s, %s)
                    ON CONFLICT (symbol, timeframe, open_time) 
                    DO UPDATE SET 
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price
                """, (SYMBOL, future_time, high_price, low_price))
        
        # Calculate outcome
        outcome = calculate_1h_outcome(SYMBOL, base_time)
        
        assert outcome['max_gain_pct_1h'] is not None
        assert outcome['max_loss_pct_1h'] is not None
        assert outcome['max_gain_pct_1h'] > 0  # Should be positive gain
        assert outcome['max_loss_pct_1h'] < 0  # Should be negative loss
    
    def test_pattern_json_size_efficiency(self, setup_test_data):
        """Test that pattern JSON is significantly smaller than full OHLC."""
        from common import SYMBOL
        from pattern_json_live import build_pattern_json
        
        # Build pattern JSON
        pattern_json = build_pattern_json(SYMBOL)
        assert pattern_json is not None
        
        # Serialize to measure size
        pattern_json_str = json.dumps(pattern_json)
        pattern_size = len(pattern_json_str)
        
        # Calculate total candles in pattern JSON
        total_candles = sum(len(candles) for candles in pattern_json['context'].values())
        
        # Verify efficiency
        assert total_candles <= 152  # Sum of all pattern limits
        assert pattern_size < 50000  # Should be reasonably compact
        
        print(f"Pattern JSON size: {pattern_size} bytes, Total candles: {total_candles}")
    
    def test_pattern_json_database_performance(self, setup_test_data):
        """Test database performance with pattern JSON."""
        from common import get_cursor, SYMBOL
        import time
        
        # Test pattern JSON query performance
        start_time = time.time()
        
        with get_cursor(dict_cursor=True) as cur:
            # Query pattern JSON with filters
            cur.execute("""
                SELECT 
                    symbol,
                    snapshot_time,
                    pattern_json->>'volatility' as volatility,
                    pattern_json->>'session' as session,
                    pattern_json->'outcome_1h'->>'max_gain_pct_1h' as max_gain_1h,
                    jsonb_array_length(pattern_json->'context'->'M1') as m1_candles,
                    jsonb_array_length(pattern_json->'context'->'H1') as h1_candles
                FROM trading_snapshots 
                WHERE symbol = %s AND pattern_json IS NOT NULL
                ORDER BY snapshot_time DESC 
                LIMIT 10
            """, (SYMBOL,))
            
            results = cur.fetchall()
        
        query_time = time.time() - start_time
        
        # Performance should be reasonable
        assert query_time < 1.0  # Less than 1 second
        print(f"Pattern JSON query time: {query_time:.3f} seconds")
    
    def test_pattern_json_vectorization_readiness(self, setup_test_data):
        """Test that pattern JSON is ready for vectorization."""
        from common import SYMBOL
        from pattern_json_live import build_pattern_json
        
        pattern_json = build_pattern_json(SYMBOL)
        assert pattern_json is not None
        
        # Test structure for vectorization
        context = pattern_json['context']
        indicators = pattern_json['indicators']
        
        # All timeframes should have consistent structure
        for timeframe, candles in context.items():
            for candle in candles:
                # Each candle should have same structure
                assert 'open' in candle
                assert 'high' in candle
                assert 'low' in candle
                assert 'close' in candle
                assert 'rsi' in candle
                assert 'ema' in candle
                assert 'atr' in candle
        
        # Indicators should be structured for easy vectorization
        for indicator_name, timeframe_values in indicators.items():
            assert isinstance(timeframe_values, dict)
            for timeframe in ['D1', 'H4', 'H1', 'M15', 'M5', 'M1']:
                assert timeframe in timeframe_values
        
        # Outcome should be numeric for analysis
        outcome = pattern_json['outcome_1h']
        if outcome['max_gain_pct_1h'] is not None:
            assert isinstance(outcome['max_gain_pct_1h'], (int, float))
        if outcome['max_loss_pct_1h'] is not None:
            assert isinstance(outcome['max_loss_pct_1h'], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
