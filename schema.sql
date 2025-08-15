-- Miando Database Schema
CREATE TABLE account_state (
    account_id TEXT,
    timestamp TIMESTAMPTZ,
    balance DOUBLE PRECISION,
    equity DOUBLE PRECISION,
    margin DOUBLE PRECISION,
    free_margin DOUBLE PRECISION,
    leverage INTEGER,
    profit DOUBLE PRECISION,
    currency TEXT
);

CREATE TABLE accounts (
    account_number BIGINT,
    active BOOLEAN
);

CREATE TABLE closed_trades (
    id INTEGER,
    symbol TEXT,
    type TEXT,
    volume NUMERIC,
    entry_price NUMERIC,
    exit_price NUMERIC,
    profit NUMERIC,
    comment TEXT,
    time TIMESTAMP,
    telegram_sent BOOLEAN,
    account_id TEXT,
    drawdown REAL
);

CREATE TABLE ohlc_data (
    id INTEGER,
    symbol VARCHAR,
    timeframe VARCHAR,
    open_time TIMESTAMP,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume BIGINT,
    adx DOUBLE PRECISION,
    atr DOUBLE PRECISION,
    bb_middle DOUBLE PRECISION,
    bb_upper DOUBLE PRECISION,
    bb_lower DOUBLE PRECISION,
    cci DOUBLE PRECISION,
    ema DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    macd_hist DOUBLE PRECISION,
    obv DOUBLE PRECISION,
    rsi DOUBLE PRECISION,
    sma DOUBLE PRECISION,
    stochastic_k DOUBLE PRECISION,
    stochastic_d DOUBLE PRECISION,
    willr DOUBLE PRECISION
);

CREATE TABLE open_trades (
    trade_id INTEGER,
    account_id TEXT,
    symbol TEXT,
    magic_number BIGINT,
    order_type TEXT,
    lot_size DOUBLE PRECISION,
    open_price DOUBLE PRECISION,
    sl DOUBLE PRECISION,
    tp DOUBLE PRECISION,
    open_time TIMESTAMPTZ,
    status TEXT,
    comment TEXT
);

CREATE TABLE planned_trades (
    id INTEGER,
    timestamp TIMESTAMPTZ,
    symbol TEXT,
    timeframe TEXT,
    action TEXT,
    order_type TEXT,
    lot_size NUMERIC,
    entry_price NUMERIC,
    sl NUMERIC,
    tp NUMERIC,
    magic_number BIGINT,
    reasoning TEXT,
    raw_response JSONB,
    new_sl NUMERIC,
    new_tp NUMERIC,
    executed BOOLEAN,
    ticket BIGINT,
    attempts INTEGER,
    original_sl NUMERIC,
    original_tp NUMERIC
);
