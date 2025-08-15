"""
Performance tests for the Miando trading system.
"""
import pytest
from unittest.mock import patch, MagicMock
import time
from concurrent.futures import ThreadPoolExecutor
import statistics

import sys
sys.path.append('/home/hazem/Miando/patterns/json_split')

from main_live import run_all_exporters_once


@pytest.mark.slow
class TestPerformance:
    """Performance benchmark tests."""
    
    def test_single_export_cycle_performance(self, benchmark):
        """Benchmark a single export cycle."""
        with patch('main_live.export_ohlc_live', return_value=True), \
             patch('main_live.export_account_state_live', return_value=True), \
             patch('main_live.export_open_trades_live', return_value=True), \
             patch('main_live.export_closed_trades_live', return_value=True), \
             patch('main_live.export_market_state_live', return_value=True):
            
            result = benchmark(run_all_exporters_once, "EURUSD")
            success_count, failed_exporters = result
            
            # Performance assertions
            assert success_count == 5
            assert len(failed_exporters) == 0
            assert benchmark.stats['mean'] < 1.0  # Should complete in under 1 second
            
    def test_database_query_performance(self, benchmark):
        """Benchmark database query performance."""
        from common import get_cursor
        
        def run_db_queries():
            with get_cursor(dict_cursor=True) as cur:
                # Simulate typical queries
                cur.execute("SELECT 1")
                cur.fetchone()
                
                cur.execute("SELECT COUNT(*) FROM trading_snapshots")
                cur.fetchone()
                
                return True
        
        with patch('common.psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = [1]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            result = benchmark(run_db_queries)
            assert result is True
            assert benchmark.stats['mean'] < 0.1  # DB queries should be fast
            
    def test_json_serialization_performance(self, benchmark):
        """Benchmark JSON serialization performance."""
        import json
        
        # Create large test data
        large_ohlc_data = {
            "M1": [
                {
                    "open_time": f"2025-08-08T10:{i:02d}:00+00:00",
                    "open": 1.0950 + i * 0.0001,
                    "high": 1.0960 + i * 0.0001,
                    "low": 1.0940 + i * 0.0001,
                    "close": 1.0955 + i * 0.0001,
                    "volume": 1000 + i * 10,
                    "adx": 25.5 + i * 0.1,
                    "atr": 0.0015 + i * 0.00001,
                    "rsi": 55.2 + i * 0.1
                }
                for i in range(1000)  # 1000 candles
            ]
        }
        
        def serialize_data():
            return json.dumps(large_ohlc_data)
        
        result = benchmark(serialize_data)
        assert len(result) > 0
        assert benchmark.stats['mean'] < 0.05  # JSON serialization should be fast
        
    def test_memory_usage(self):
        """Test memory usage during operations."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Run a typical export cycle
        with patch('main_live.export_ohlc_live', return_value=True), \
             patch('main_live.export_account_state_live', return_value=True), \
             patch('main_live.export_open_trades_live', return_value=True), \
             patch('main_live.export_closed_trades_live', return_value=True), \
             patch('main_live.export_market_state_live', return_value=True):
            
            run_all_exporters_once("EURUSD")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (less than 50MB)
        assert peak < 50 * 1024 * 1024  # 50MB
        
    def test_concurrent_export_performance(self):
        """Test performance under concurrent load."""
        def run_export():
            with patch('main_live.export_ohlc_live', return_value=True), \
                 patch('main_live.export_account_state_live', return_value=True), \
                 patch('main_live.export_open_trades_live', return_value=True), \
                 patch('main_live.export_closed_trades_live', return_value=True), \
                 patch('main_live.export_market_state_live', return_value=True):
                
                start_time = time.time()
                run_all_exporters_once("EURUSD")
                return time.time() - start_time
        
        # Run 10 concurrent exports
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_export) for _ in range(10)]
            execution_times = [future.result() for future in futures]
        
        # All should complete
        assert len(execution_times) == 10
        
        # Average time should still be reasonable
        avg_time = statistics.mean(execution_times)
        assert avg_time < 2.0  # Even under load, should complete in under 2 seconds
        
        # No execution should take too long
        max_time = max(execution_times)
        assert max_time < 5.0  # No single execution should take more than 5 seconds


@pytest.mark.slow
class TestLoadTesting:
    """Load testing scenarios."""
    
    def test_sustained_load(self):
        """Test system behavior under sustained load."""
        execution_times = []
        
        def run_single_cycle():
            with patch('main_live.export_ohlc_live', return_value=True), \
                 patch('main_live.export_account_state_live', return_value=True), \
                 patch('main_live.export_open_trades_live', return_value=True), \
                 patch('main_live.export_closed_trades_live', return_value=True), \
                 patch('main_live.export_market_state_live', return_value=True):
                
                start_time = time.time()
                run_all_exporters_once("EURUSD")
                return time.time() - start_time
        
        # Run 100 consecutive cycles
        for i in range(100):
            exec_time = run_single_cycle()
            execution_times.append(exec_time)
            
            # Brief pause to simulate real-world timing
            time.sleep(0.01)
        
        # Check for performance degradation
        first_10 = statistics.mean(execution_times[:10])
        last_10 = statistics.mean(execution_times[-10:])
        
        # Performance should not degrade by more than 50%
        assert last_10 < first_10 * 1.5
        
        # Overall average should be acceptable
        overall_avg = statistics.mean(execution_times)
        assert overall_avg < 1.0
        
    def test_burst_load(self):
        """Test system behavior under burst load."""
        def burst_exports():
            execution_times = []
            
            # Rapid-fire 20 exports
            for _ in range(20):
                with patch('main_live.export_ohlc_live', return_value=True), \
                     patch('main_live.export_account_state_live', return_value=True), \
                     patch('main_live.export_open_trades_live', return_value=True), \
                     patch('main_live.export_closed_trades_live', return_value=True), \
                     patch('main_live.export_market_state_live', return_value=True):
                    
                    start_time = time.time()
                    run_all_exporters_once("EURUSD")
                    execution_times.append(time.time() - start_time)
            
            return execution_times
        
        burst_times = burst_exports()
        
        # All exports should complete
        assert len(burst_times) == 20
        
        # No single export should take too long even under burst
        max_time = max(burst_times)
        assert max_time < 2.0
        
        # Average should still be reasonable
        avg_time = statistics.mean(burst_times)
        assert avg_time < 1.0


@pytest.mark.slow
class TestScalabilityTesting:
    """Test system scalability."""
    
    def test_data_volume_scaling(self):
        """Test performance with varying data volumes."""
        from common import insert_snapshot
        from datetime import datetime, timezone
        
        # Test with different data sizes
        data_sizes = [100, 1000, 10000]  # Number of data points
        execution_times = {}
        
        for size in data_sizes:
            # Create test data of specified size
            large_data = {
                "test_data": [
                    {"id": i, "value": f"data_{i}", "timestamp": f"2025-08-08T10:{i%60:02d}:00+00:00"}
                    for i in range(size)
                ]
            }
            
            with patch('common.get_cursor') as mock_get_cursor:
                mock_cursor = MagicMock()
                mock_get_cursor.return_value.__enter__.return_value = mock_cursor
                
                start_time = time.time()
                insert_snapshot(
                    symbol="TEST",
                    snapshot_time=datetime(2025, 8, 8, 10, 0, 0, tzinfo=timezone.utc),
                    json_column_name="test_json",
                    json_data=large_data
                )
                execution_times[size] = time.time() - start_time
        
        # Performance should scale reasonably
        # 10x data should not take more than 10x time
        if len(execution_times) >= 2:
            smallest_size = min(data_sizes)
            largest_size = max(data_sizes)
            
            time_ratio = execution_times[largest_size] / execution_times[smallest_size]
            size_ratio = largest_size / smallest_size
            
            # Time scaling should be better than linear
            assert time_ratio < size_ratio * 1.5
            
    def test_concurrent_symbol_processing(self):
        """Test processing multiple symbols concurrently."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
        
        def process_symbol(symbol):
            with patch('main_live.export_ohlc_live', return_value=True), \
                 patch('main_live.export_account_state_live', return_value=True), \
                 patch('main_live.export_open_trades_live', return_value=True), \
                 patch('main_live.export_closed_trades_live', return_value=True), \
                 patch('main_live.export_market_state_live', return_value=True):
                
                start_time = time.time()
                run_all_exporters_once(symbol)
                return time.time() - start_time
        
        # Process all symbols concurrently
        with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
            futures = {executor.submit(process_symbol, symbol): symbol for symbol in symbols}
            results = {}
            
            for future in futures:
                symbol = futures[future]
                results[symbol] = future.result()
        
        # All symbols should be processed
        assert len(results) == len(symbols)
        
        # No symbol should take too long
        max_time = max(results.values())
        assert max_time < 3.0
        
        # Average time should be reasonable
        avg_time = statistics.mean(results.values())
        assert avg_time < 1.5


@pytest.mark.slow 
class TestStressTesting:
    """Stress testing scenarios."""
    
    def test_error_recovery_under_load(self):
        """Test error recovery under high load."""
        success_count = 0
        error_count = 0
        
        def failing_export():
            nonlocal success_count, error_count
            
            # Simulate random failures (30% failure rate)
            import random
            if random.random() < 0.3:
                error_count += 1
                raise Exception("Simulated failure")
            else:
                success_count += 1
                return True
        
        # Run many cycles with failures
        for _ in range(100):
            try:
                with patch('main_live.export_ohlc_live', side_effect=failing_export), \
                     patch('main_live.export_account_state_live', return_value=True), \
                     patch('main_live.export_open_trades_live', return_value=True), \
                     patch('main_live.export_closed_trades_live', return_value=True), \
                     patch('main_live.export_market_state_live', return_value=True):
                    
                    run_all_exporters_once("EURUSD")
            except Exception:
                # System should handle exceptions gracefully
                pass
        
        # Should have processed all attempts
        assert (success_count + error_count) >= 90  # Allow for some variance
        
    def test_resource_exhaustion_protection(self):
        """Test protection against resource exhaustion."""
        # This test would check memory leaks, file handle leaks, etc.
        import gc
        import resource
        
        initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Run many cycles
        for _ in range(50):
            with patch('main_live.export_ohlc_live', return_value=True), \
                 patch('main_live.export_account_state_live', return_value=True), \
                 patch('main_live.export_open_trades_live', return_value=True), \
                 patch('main_live.export_closed_trades_live', return_value=True), \
                 patch('main_live.export_market_state_live', return_value=True):
                
                run_all_exporters_once("EURUSD")
            
            # Force garbage collection
            gc.collect()
        
        final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 10MB)
        assert memory_increase < 10 * 1024  # 10MB in KB
