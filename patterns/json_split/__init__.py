#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSON Split Package for Miando Trading System

This package splits the monolithic json_exporter.py into separate components:
- ohlc_all_live.py: OHLC data with indicators for all timeframes
- account_state_live.py: Account balance, equity, margin data
- open_trades_live.py: Currently open and pending trades
- closed_trades_live.py: Recently closed trades
- market_state_live.py: Market volatility, spread, session data

Each component exports data to separate JSONB columns in the trading_snapshots table.
"""

__version__ = "1.0.0"
__author__ = "Miando Team"

# Export main functions for easy importing
from .common import get_pg_conn, insert_snapshot, get_latest_m1_time, get_latest_account_id
from .ohlc_all_live import export_ohlc_all_live
from .account_state_live import export_account_state_live  
from .open_trades_live import export_open_trades_live
from .closed_trades_live import export_closed_trades_live
from .market_state_live import export_market_state_live

__all__ = [
    'get_pg_conn',
    'insert_snapshot', 
    'get_latest_m1_time',
    'get_latest_account_id',
    'export_ohlc_all_live',
    'export_account_state_live',
    'export_open_trades_live',
    'export_closed_trades_live',
    'export_market_state_live'
]
