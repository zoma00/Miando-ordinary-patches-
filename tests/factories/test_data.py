"""
Test data factories for generating realistic test data.
"""
import factory
from factory import Faker, LazyFunction
from datetime import datetime, timezone, timedelta
import random
from decimal import Decimal


class OHLCDataFactory(factory.Factory):
    """Factory for generating OHLC candlestick data."""
    
    class Meta:
        model = dict
    
    open_time = LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 1440)))
    open = Faker('pydecimal', left_digits=1, right_digits=4, positive=True, min_value=Decimal('1.0000'), max_value=Decimal('2.0000'))
    high = factory.LazyAttribute(lambda obj: obj.open + Decimal(str(random.uniform(0.0001, 0.0100))))
    low = factory.LazyAttribute(lambda obj: obj.open - Decimal(str(random.uniform(0.0001, 0.0100))))
    close = factory.LazyAttribute(lambda obj: obj.open + Decimal(str(random.uniform(-0.0050, 0.0050))))
    volume = Faker('pyint', min_value=100, max_value=10000)
    
    # Technical indicators
    adx = Faker('pyfloat', min_value=0, max_value=100, right_digits=2)
    atr = Faker('pyfloat', min_value=0.0001, max_value=0.0100, right_digits=4)
    bb_middle = factory.LazyAttribute(lambda obj: obj.close)
    bb_upper = factory.LazyAttribute(lambda obj: obj.bb_middle + Decimal(str(random.uniform(0.0010, 0.0050))))
    bb_lower = factory.LazyAttribute(lambda obj: obj.bb_middle - Decimal(str(random.uniform(0.0010, 0.0050))))
    cci = Faker('pyfloat', min_value=-300, max_value=300, right_digits=2)
    ema = factory.LazyAttribute(lambda obj: obj.close + Decimal(str(random.uniform(-0.0020, 0.0020))))
    macd = Faker('pyfloat', min_value=-0.0100, max_value=0.0100, right_digits=4)
    macd_signal = factory.LazyAttribute(lambda obj: obj.macd + random.uniform(-0.0010, 0.0010))
    macd_hist = factory.LazyAttribute(lambda obj: obj.macd - obj.macd_signal)
    obv = Faker('pyint', min_value=-100000, max_value=100000)
    rsi = Faker('pyfloat', min_value=0, max_value=100, right_digits=2)
    sma = factory.LazyAttribute(lambda obj: obj.close + Decimal(str(random.uniform(-0.0030, 0.0030))))
    stochastic_k = Faker('pyfloat', min_value=0, max_value=100, right_digits=2)
    stochastic_d = factory.LazyAttribute(lambda obj: obj.stochastic_k + random.uniform(-10, 10))
    willr = Faker('pyfloat', min_value=-100, max_value=0, right_digits=2)


class AccountStateFactory(factory.Factory):
    """Factory for generating account state data."""
    
    class Meta:
        model = dict
    
    timestamp = LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    balance = Faker('pyfloat', min_value=1000, max_value=100000, right_digits=2)
    equity = factory.LazyAttribute(lambda obj: obj.balance + random.uniform(-500, 500))
    margin = Faker('pyfloat', min_value=0, max_value=5000, right_digits=2)
    free_margin = factory.LazyAttribute(lambda obj: obj.equity - obj.margin)
    leverage = Faker('random_element', elements=[50, 100, 200, 500])
    profit = factory.LazyAttribute(lambda obj: obj.equity - obj.balance)
    currency = Faker('random_element', elements=['USD', 'EUR', 'GBP'])


class TradeFactory(factory.Factory):
    """Factory for generating trade data."""
    
    class Meta:
        model = dict
    
    symbol = Faker('random_element', elements=['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'])
    magic = Faker('pyint', min_value=10000, max_value=99999)
    order_type = Faker('random_element', elements=['buy', 'sell', 'buy_limit', 'sell_limit', 'buy_stop', 'sell_stop'])
    lot_size = Faker('pyfloat', min_value=0.01, max_value=10.0, right_digits=2)
    open_price = Faker('pyfloat', min_value=1.0000, max_value=2.0000, right_digits=4)
    sl = factory.LazyAttribute(lambda obj: obj.open_price - 0.0100 if obj.order_type.startswith('buy') else obj.open_price + 0.0100)
    tp = factory.LazyAttribute(lambda obj: obj.open_price + 0.0100 if obj.order_type.startswith('buy') else obj.open_price - 0.0100)
    profit = Faker('pyfloat', min_value=-1000, max_value=1000, right_digits=2)
    open_time = LazyFunction(lambda: (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24))).isoformat())
    status = Faker('random_element', elements=['open', 'pending', 'closed'])
    comment = Faker('sentence', nb_words=3)


class ClosedTradeFactory(TradeFactory):
    """Factory for generating closed trade data."""
    
    close_price = factory.LazyAttribute(lambda obj: obj.open_price + random.uniform(-0.0200, 0.0200))
    close_time = LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    duration_minutes = Faker('pyint', min_value=1, max_value=1440)
    status = 'closed'


class MarketStateFactory(factory.Factory):
    """Factory for generating market state data."""
    
    class Meta:
        model = dict
    
    volatility = Faker('random_element', elements=['low', 'medium', 'high'])
    spread = Faker('pyfloat', min_value=0.5, max_value=5.0, right_digits=1)
    session = Faker('random_element', elements=['Sydney', 'Tokyo', 'London', 'New York'])
    news_event = Faker('boolean', chance_of_getting_true=20)  # 20% chance of news event


class TradingSnapshotFactory(factory.Factory):
    """Factory for generating complete trading snapshots."""
    
    class Meta:
        model = dict
    
    symbol = Faker('random_element', elements=['EURUSD', 'GBPUSD', 'USDJPY'])
    snapshot_time = LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    
    # JSON data fields
    ohlc_all_json = factory.LazyFunction(lambda: {
        'M1': OHLCDataFactory.build_batch(10),
        'M5': OHLCDataFactory.build_batch(5),
        'M15': OHLCDataFactory.build_batch(3),
        'H1': OHLCDataFactory.build_batch(2),
        'H4': OHLCDataFactory.build_batch(1),
        'D1': OHLCDataFactory.build_batch(1)
    })
    
    account_state_json = factory.SubFactory(AccountStateFactory)
    open_trades_json = factory.LazyFunction(lambda: TradeFactory.build_batch(random.randint(0, 5)))
    closed_trades_json = factory.LazyFunction(lambda: ClosedTradeFactory.build_batch(random.randint(0, 3)))
    market_state_json = factory.SubFactory(MarketStateFactory)


# Utility functions for test data generation

def create_realistic_ohlc_sequence(count: int, start_price: float = 1.1000, timeframe: str = 'M1'):
    """Create a realistic sequence of OHLC data with trending behavior."""
    sequence = []
    current_price = start_price
    
    # Determine time delta based on timeframe
    time_deltas = {
        'M1': timedelta(minutes=1),
        'M5': timedelta(minutes=5),
        'M15': timedelta(minutes=15),
        'H1': timedelta(hours=1),
        'H4': timedelta(hours=4),
        'D1': timedelta(days=1)
    }
    delta = time_deltas.get(timeframe, timedelta(minutes=1))
    
    start_time = datetime.now(timezone.utc) - (delta * count)
    
    for i in range(count):
        # Add some trending behavior
        trend = random.uniform(-0.0005, 0.0005)
        volatility = random.uniform(0.0001, 0.0020)
        
        open_price = current_price
        high = open_price + random.uniform(0, volatility)
        low = open_price - random.uniform(0, volatility)
        close = open_price + trend + random.uniform(-volatility/2, volatility/2)
        
        # Ensure high is highest and low is lowest
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        candle = OHLCDataFactory.build(
            open_time=start_time + (delta * i),
            open=round(open_price, 4),
            high=round(high, 4),
            low=round(low, 4),
            close=round(close, 4)
        )
        
        sequence.append(candle)
        current_price = close
    
    return sequence


def create_test_database_data(db_cursor, symbol: str = "TEST_EURUSD"):
    """Insert test data into the database for testing."""
    
    # Insert OHLC data
    ohlc_data = create_realistic_ohlc_sequence(100, 1.1000, 'M1')
    for candle in ohlc_data:
        db_cursor.execute("""
            INSERT INTO ohlc_data (
                symbol, timeframe, open_time, open, high, low, close, volume,
                adx, atr, rsi
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            symbol, 'M1', candle['open_time'], candle['open'], candle['high'],
            candle['low'], candle['close'], candle['volume'], candle['adx'],
            candle['atr'], candle['rsi']
        ))
    
    # Insert account state
    account_data = AccountStateFactory.build()
    db_cursor.execute("""
        INSERT INTO account_state (
            account_id, timestamp, balance, equity, margin, free_margin, leverage, profit, currency
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        "12345", account_data['timestamp'], account_data['balance'],
        account_data['equity'], account_data['margin'], account_data['free_margin'],
        account_data['leverage'], account_data['profit'], account_data['currency']
    ))
    
    # Insert some trades
    for _ in range(3):
        trade = TradeFactory.build(symbol=symbol)
        db_cursor.execute("""
            INSERT INTO open_trades (
                account_id, symbol, magic, order_type, lot, open_price, sl, tp, open_time, status, comment
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "12345", trade['symbol'], trade['magic'], trade['order_type'],
            trade['lot_size'], trade['open_price'], trade['sl'], trade['tp'],
            trade['open_time'], trade['status'], trade['comment']
        ))


def cleanup_test_data(db_cursor, symbol: str = "TEST_EURUSD"):
    """Clean up test data from the database."""
    db_cursor.execute("DELETE FROM trading_snapshots WHERE symbol = %s", (symbol,))
    db_cursor.execute("DELETE FROM ohlc_data WHERE symbol = %s", (symbol,))
    db_cursor.execute("DELETE FROM open_trades WHERE symbol = %s", (symbol,))
    db_cursor.execute("DELETE FROM closed_trades WHERE symbol = %s", (symbol,))
    db_cursor.execute("DELETE FROM account_state WHERE account_id = %s", ("12345",))
