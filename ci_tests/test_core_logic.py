"""Fast, offline tests for Miando's core integration and analytics logic."""

from datetime import datetime, timezone

import pytest

from data_bridge import AmirDataBridge
from patterns.json_split.common import (
    format_timestamp_utc,
    safe_float,
    safe_float_nullable,
    safe_int,
)
from patterns.json_split.ohlc_all_live import build_ohlc_last_time
from patterns.json_split.pattern_json_live import assess_volatility, get_trading_session


@pytest.mark.parametrize(
    ("value", "expected"),
    [("42.5", 42.5), (42, 42.0), (None, 0.0), ("invalid", 0.0)],
)
def test_safe_float(value, expected):
    assert safe_float(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("42", 42), (42.9, 42), (None, 0), ("invalid", 0)],
)
def test_safe_int(value, expected):
    assert safe_int(value) == expected


def test_safe_float_nullable_preserves_missing_values():
    assert safe_float_nullable(None) is None
    assert safe_float_nullable("invalid") is None
    assert safe_float_nullable("3.25") == 3.25


def test_format_timestamp_utc_normalizes_timezone():
    timestamp = datetime(2025, 8, 8, 12, 30, tzinfo=timezone.utc)
    assert format_timestamp_utc(timestamp) == "2025-08-08T12:30:00+00:00"
    assert format_timestamp_utc(None) is None


def test_build_ohlc_last_time_uses_latest_candle():
    candles = {
        "M1": [
            {"open_time": "2025-08-08T12:29:00+00:00"},
            {"open_time": "2025-08-08T12:30:00+00:00"},
        ],
        "H1": [],
    }

    assert build_ohlc_last_time(candles) == {
        "M1": "2025-08-08T12:30:00+00:00",
        "H1": None,
    }


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(22, "Sydney"), (6, "Sydney"), (7, "London"), (14, "London"), (15, "New York")],
)
def test_pattern_trading_session_boundaries(hour, expected):
    timestamp = datetime(2025, 8, 8, hour, tzinfo=timezone.utc)
    assert get_trading_session(timestamp) == expected


@pytest.mark.parametrize(
    ("atr_values", "expected"),
    [({"H1": 16.0}, "high"), ({"H1": 10.0}, "medium"), ({"H1": 4.0}, "low")],
)
def test_assess_volatility_from_hourly_atr(atr_values, expected):
    assert assess_volatility(atr_values) == expected


def test_assess_volatility_falls_back_to_price_range():
    assert assess_volatility({}, {"price_range_4h": 21.0}) == "high_price"
    assert assess_volatility({}, {}) == "no_data"


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(22, "Sydney"), (6, "Sydney"), (7, "London"), (14, "London"), (15, "New_York")],
)
def test_bridge_trading_session_boundaries(hour, expected):
    timestamp = datetime(2025, 8, 8, hour, tzinfo=timezone.utc)
    assert AmirDataBridge().get_trading_session(timestamp) == expected


def test_bridge_volatility_score():
    bridge = AmirDataBridge()
    record = {"high_price": 101.0, "low_price": 99.0, "open_price": 100.0}

    assert bridge.calculate_volatility_score(record) == 2.0
    assert bridge.calculate_volatility_score({"open_price": 0}) == 0.0


def test_bridge_enriches_ohlc_record():
    bridge = AmirDataBridge()
    record = {
        "symbol": "EURUSD",
        "open_time": datetime(2025, 8, 8, 8, tzinfo=timezone.utc),
        "open_price": 1.1,
        "high_price": 1.102,
        "low_price": 1.099,
        "close_price": 1.101,
        "spread": 0,
    }

    enriched = bridge.enhance_ohlc_record(record)

    assert enriched["estimated_spread"] == 0.00015
    assert enriched["trading_session"] == "London"
    assert enriched["volatility_score"] == pytest.approx(0.2727)
    assert enriched["price_change_pct"] == pytest.approx(0.0909)
    assert enriched["bridge_processed_at"].tzinfo is None
