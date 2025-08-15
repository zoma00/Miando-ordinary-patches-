import os
import time
import numpy as np
import pandas as pd
from datetime import timedelta
from sqlalchemy import create_engine, text
from psycopg2.extras import execute_values

# ==================== CONFIG ====================
DB_HOST = os.getenv('DB_HOST', 'miando-db')
DB_PORT = os.getenv('DB_PORT', '5434')
DB_NAME = os.getenv('DB_NAME', 'miando')
DB_USER = os.getenv('DB_USER', 'miando')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'changeme')
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', '/app/server.crt')

# Live-Check alle 15s
POLL_SECONDS = int(os.getenv('POLL_SECONDS', '15'))

# Für jede Berechnung: so viele Kerzen VOR dem Zieltimestamp verwenden
LOOKBACK_N = int(os.getenv('LOOKBACK_N', '300'))  # 300 = stabil für MACD/ADX/RSI (Warm-up)

# Historischer Backfill: pro Batch so viele Zielzeilen rechnen & updaten
CHUNK_ROWS = int(os.getenv('CHUNK_ROWS', '100000'))  # Increased from 20k to 100k for faster processing

# Page size für execute_values (Temp-Table bulk insert)
PAGE_SIZE_VALUES = int(os.getenv('PAGE_SIZE_VALUES', '50000'))  # Increased from 10k to 50k for faster bulk inserts

# Timeframe-Sekunden
TF_SECONDS = {"M1":60, "M5":300, "M15":900, "M30":1800, "H1":3600, "H4":14400, "D1":86400}

INDICATOR_COLUMNS = [
    "adx","atr","bb_upper","bb_middle","bb_lower","cci","ema",
    "macd","macd_signal","macd_hist","obv","rsi","sma",
    "stochastic_k","stochastic_d","willr"
]
INDICATOR_NULL_PRED = " OR ".join([f"{c} IS NULL" for c in INDICATOR_COLUMNS])

# ==================== DB URL ====================
if os.path.exists(SSL_CERT_PATH):
    DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require&sslrootcert={SSL_CERT_PATH}"
else:
    print("⚠️ SSL-Zertifikat nicht gefunden – Verbindung ohne SSL.")
    DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"🔗 Connecting to DB {DB_HOST}:{DB_PORT}/{DB_NAME}")
engine = create_engine(DB_URL, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

# ==================== Indicator Calc (Wilder/RMA-Varianten) ====================
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Erwartet: open_time, high_price, low_price, close_price, volume.
    Berechnet Indikatoren mit Wilder-Smoothing (ATR, ADX, RSI als RMA).
    """
    df = df.copy()

    h = df["high_price"].astype(float)
    l = df["low_price"].astype(float)
    c = df["close_price"].astype(float)
    v = df["volume"].astype(float)

    # --- ATR (Wilder/RMA auf True Range) ---
    tr = pd.DataFrame({
        "tr1": (h - l),
        "tr2": (h - c.shift()).abs(),
        "tr3": (l - c.shift()).abs()
    }).max(axis=1)
    atr = tr.ewm(alpha=1/14, adjust=False).mean()
    df["atr"] = atr

    # --- ADX/DI (Wilder/RMA) ---
    up   = h.diff()
    down = -l.diff()  # Low[t-1] - Low[t]
    plus_dm  = np.where((up > 0) & (up > down),  up,   0.0)
    minus_dm = np.where((down > 0) & (down > up), down, 0.0)
    plus_di  = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr.replace(0, np.nan)
    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    df["adx"] = dx.ewm(alpha=1/14, adjust=False).mean()

    # --- Bollinger (20, 2σ) ---
    mid = c.rolling(20).mean()
    std = c.rolling(20).std()
    df["bb_middle"] = mid
    df["bb_upper"]  = mid + 2*std
    df["bb_lower"]  = mid - 2*std

    # --- CCI (20) ---
    tp = (h + l + c) / 3.0
    sma_tp = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    mad = mad.replace(0, np.nan)
    df["cci"] = (tp - sma_tp) / (0.015 * mad)

    # --- EMA(20) ---
    df["ema"] = c.ewm(span=20, adjust=False).mean()

    # --- MACD (12,26,9) ---
    ema_fast = c.ewm(span=12, adjust=False).mean()
    ema_slow = c.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9, adjust=False).mean()
    df["macd"] = macd
    df["macd_signal"] = signal
    df["macd_hist"] = macd - signal

    # --- OBV ---
    obv = [0.0]
    for i in range(1, len(c)):
        if c.iloc[i] > c.iloc[i-1]:
            obv.append(obv[-1] + v.iloc[i])
        elif c.iloc[i] < c.iloc[i-1]:
            obv.append(obv[-1] - v.iloc[i])
        else:
            obv.append(obv[-1])
    df["obv"] = obv

    # --- RSI(14) als Wilder-RSI (RMA) ---
    delta = c.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    rma_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    rma_loss = loss.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    rs = rma_gain / rma_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # --- SMA(14) ---
    df["sma"] = c.rolling(14).mean()

    # --- Stochastic (14,3) ---
    low_min  = l.rolling(14).min()
    high_max = h.rolling(14).max()
    den = (high_max - low_min).replace(0, np.nan)
    k = 100 * (c - low_min) / den
    d = k.rolling(3).mean()
    df["stochastic_k"] = k
    df["stochastic_d"] = d

    # --- Williams %R(14) ---
    high_max = h.rolling(14).max()
    low_min  = l.rolling(14).min()
    den2 = (high_max - low_min).replace(0, np.nan)
    df["willr"] = -100 * (high_max - c) / den2

    return df

# ==================== Helpers ====================
def get_symbol_timeframes(conn):
    return conn.execute(text("SELECT DISTINCT symbol, timeframe FROM ohlc_data ORDER BY 1,2")).fetchall()

def earliest_null_row(conn, symbol, timeframe):
    sql = f"""
        SELECT MIN(open_time) AS first_null
        FROM ohlc_data
        WHERE symbol=:s AND timeframe=:tf AND ({INDICATOR_NULL_PRED})
    """
    r = conn.execute(text(sql), {"s":symbol, "tf":timeframe}).scalar()
    return r  # None wenn keine Lücke

def fetch_range_by_time(conn, symbol, timeframe, start_ts, end_ts):
    cols = ", ".join(["symbol","timeframe","open_time",
                      "open_price","high_price","low_price","close_price","volume"] + INDICATOR_COLUMNS)
    sql = f"""
        SELECT {cols}
        FROM ohlc_data
        WHERE symbol=:s AND timeframe=:tf AND open_time BETWEEN :a AND :b
        ORDER BY open_time ASC
    """
    return pd.read_sql(text(sql), conn, params={"s":symbol, "tf":timeframe, "a":start_ts, "b":end_ts})

def fetch_tail(conn, symbol, timeframe, limit_rows):
    cols = ", ".join(["symbol","timeframe","open_time",
                      "open_price","high_price","low_price","close_price","volume"] + INDICATOR_COLUMNS)
    sql = f"""
        SELECT {cols}
        FROM ohlc_data
        WHERE symbol=:s AND timeframe=:tf
        ORDER BY open_time DESC
        LIMIT :lim
    """
    df = pd.read_sql(text(sql), conn, params={"s":symbol, "tf":timeframe, "lim":limit_rows})
    return df.sort_values("open_time")

def build_rows_for_update(df_calc, df_db_subset):
    """Baue Werte für Batch-Update: nur Zeilen, wo DB noch NULLs hat."""
    dfm = df_db_subset[["open_time","symbol","timeframe"] + INDICATOR_COLUMNS].copy()
    need = dfm[INDICATOR_COLUMNS].isnull().any(axis=1)
    if not need.any():
        return []

    # Join calc auf open_time
    calc_cols = ["open_time"] + INDICATOR_COLUMNS
    merged = pd.merge(dfm[["open_time","symbol","timeframe"]], df_calc[calc_cols], on="open_time", how="left")

    rows = []
    for _, r in merged.loc[need].iterrows():
        rows.append((
            r["symbol"], r["timeframe"], pd.to_datetime(r["open_time"]).to_pydatetime(),
            float(r["adx"]) if pd.notnull(r["adx"]) else None,
            float(r["atr"]) if pd.notnull(r["atr"]) else None,
            float(r["bb_upper"]) if pd.notnull(r["bb_upper"]) else None,
            float(r["bb_middle"]) if pd.notnull(r["bb_middle"]) else None,
            float(r["bb_lower"]) if pd.notnull(r["bb_lower"]) else None,
            float(r["cci"]) if pd.notnull(r["cci"]) else None,
            float(r["ema"]) if pd.notnull(r["ema"]) else None,
            float(r["macd"]) if pd.notnull(r["macd"]) else None,
            float(r["macd_signal"]) if pd.notnull(r["macd_signal"]) else None,
            float(r["macd_hist"]) if pd.notnull(r["macd_hist"]) else None,
            float(r["obv"]) if pd.notnull(r["obv"]) else None,
            float(r["rsi"]) if pd.notnull(r["rsi"]) else None,
            float(r["sma"]) if pd.notnull(r["sma"]) else None,
            float(r["stochastic_k"]) if pd.notnull(r["stochastic_k"]) else None,
            float(r["stochastic_d"]) if pd.notnull(r["stochastic_d"]) else None,
            float(r["willr"]) if pd.notnull(r["willr"]) else None
        ))
    return rows

def batch_update(conn, rows):
    """TURBO batch update with auto-commit (prevents transaction conflicts)."""
    if not rows:
        return 0
    
    updated = 0
    chunk_size = min(500, len(rows))  # Smaller chunks for stability
    
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        chunk_updated = 0
        
        # Process each row with auto-commit
        for row in chunk:
            try:
                symbol, timeframe, open_time, adx, atr, bb_upper, bb_middle, bb_lower, cci, ema, macd, macd_signal, macd_hist, obv, rsi, sma, stochastic_k, stochastic_d, willr = row
                
                # Simplified UPDATE without NULL check in WHERE clause (prevents infinite loops)
                sql = text("""
                    UPDATE ohlc_data 
                    SET adx=:adx, atr=:atr, bb_upper=:bb_upper, bb_middle=:bb_middle, bb_lower=:bb_lower,
                        cci=:cci, ema=:ema, macd=:macd, macd_signal=:macd_signal, macd_hist=:macd_hist,
                        obv=:obv, rsi=:rsi, sma=:sma, stochastic_k=:stochastic_k, stochastic_d=:stochastic_d, willr=:willr
                    WHERE symbol=:symbol AND timeframe=:timeframe AND open_time=:open_time
                """)
                
                result = conn.execute(sql, {
                    'symbol': symbol, 'timeframe': timeframe, 'open_time': open_time,
                    'adx': adx, 'atr': atr, 'bb_upper': bb_upper, 'bb_middle': bb_middle, 'bb_lower': bb_lower,
                    'cci': cci, 'ema': ema, 'macd': macd, 'macd_signal': macd_signal, 'macd_hist': macd_hist,
                    'obv': obv, 'rsi': rsi, 'sma': sma, 'stochastic_k': stochastic_k, 'stochastic_d': stochastic_d, 'willr': willr
                })
                chunk_updated += result.rowcount
                
            except Exception as e:
                print(f"⚠️ Row update failed: {e}")
                continue
        
        updated += chunk_updated
        print(f"⚡ TURBO chunk {i//chunk_size + 1}/{(len(rows)-1)//chunk_size + 1}: {chunk_updated} rows updated")
    
    return updated

# ==================== Backfill (historisch, schnell) ====================
def historical_backfill(conn, symbol, timeframe):
    """
    TURBO backfill with infinite loop protection.
    Arbeitet Lücken in großen Blöcken ab mit Safety-Mechanismen.
    """
    tf_sec = TF_SECONDS.get(timeframe)
    if tf_sec is None:
        print(f"⚠️ Unbekannter TF '{timeframe}' – Backfill übersprungen.")
        return 0

    total_upd = 0
    iteration_count = 0
    max_iterations = 50  # Safety limit to prevent infinite loops
    
    while iteration_count < max_iterations:
        iteration_count += 1
        first_null = earliest_null_row(conn, symbol, timeframe)
        
        if first_null is None:
            print(f"✅ {symbol} {timeframe}: No more gaps found after {iteration_count} iterations")
            break  # alles fertig

        start_ts = first_null - timedelta(seconds=LOOKBACK_N * tf_sec)
        end_ts   = first_null + timedelta(seconds=CHUNK_ROWS * tf_sec)

        df = fetch_range_by_time(conn, symbol, timeframe, start_ts, end_ts)
        if df.empty:
            print(f"⚠️ {symbol} {timeframe}: No data found for range, breaking")
            break

        # Rechnen (mit Lookback). Für Updates nur der Teil ab first_null relevant.
        df_calc = calculate_indicators(df[["open_time","high_price","low_price","close_price","volume"]].copy())
        df_calc = pd.concat(
            [df[["open_time","symbol","timeframe"]].reset_index(drop=True),
             df_calc.drop(columns=["open_time"], errors="ignore")],
            axis=1
        )

        df_subset = df[df["open_time"] >= first_null][["open_time","symbol","timeframe"] + INDICATOR_COLUMNS]
        rows = build_rows_for_update(df_calc, df_subset)
        
        if not rows:
            print(f"⚠️ {symbol} {timeframe}: No rows to update, breaking at iteration {iteration_count}")
            break

        # Use transaction-safe batch update
        updated = batch_update(conn, rows)
        total_upd += updated
        
        if updated == 0:
            print(f"⚠️ {symbol} {timeframe}: No rows actually updated, breaking to prevent infinite loop")
            break
            
        print(f"🚀 TURBO Backfill {symbol} {timeframe}: +{updated} (bis {df_subset['open_time'].max()}) [iter {iteration_count}]")

    if iteration_count >= max_iterations:
        print(f"⚠️ {symbol} {timeframe}: Reached max iterations ({max_iterations}), stopping to prevent infinite loop")

    return total_upd

# ==================== Live-Update (alle 15s) ====================
def live_update_once(conn, symbol, timeframe):
    """
    Zieht die letzten LOOKBACK_N+10 Bars (abgeschlossen), berechnet frisch,
    und updatet nur Zeilen, die noch NULLs haben.
    """
    df_tail = fetch_tail(conn, symbol, timeframe, LOOKBACK_N + 10)
    if len(df_tail) < max(35, LOOKBACK_N//2):
        return 0

    df_calc = calculate_indicators(df_tail[["open_time","high_price","low_price","close_price","volume"]].copy())
    df_calc = pd.concat(
        [df_tail[["open_time","symbol","timeframe"]].reset_index(drop=True),
         df_calc.drop(columns=["open_time"], errors="ignore")],
        axis=1
    )

    rows = build_rows_for_update(df_calc, df_tail[["open_time","symbol","timeframe"] + INDICATOR_COLUMNS])
    if not rows:
        return 0

    # Use simple connection for batch update
    updated = batch_update(conn, rows)
    return updated

# ==================== OPTIMIZED PROCESSING ====================
def prioritized_backfill():
    """
    Smart backfill: Process recent data first (2024-2025), then older data.
    This ensures trading-relevant data gets calculated first.
    """
    with engine.connect() as conn:
        combos = get_symbol_timeframes(conn)
    
    print("🎯 Phase 1: Processing recent data (2024-2025) first...")
    
    # Phase 1: Recent data (last 2 years) - higher priority
    recent_updated = 0
    for symbol, timeframe in combos:
        with engine.connect() as conn:
            # Check if there are recent nulls (2024+)
            recent_nulls = conn.execute(text(f"""
                SELECT COUNT(*) FROM ohlc_data 
                WHERE symbol=:s AND timeframe=:tf 
                AND open_time >= '2024-01-01' 
                AND ({INDICATOR_NULL_PRED})
            """), {"s": symbol, "tf": timeframe}).scalar()
            
            if recent_nulls > 0:
                print(f"⚡ Priority: {symbol} | {timeframe} ({recent_nulls} recent gaps)")
                recent_updated += historical_backfill(conn, symbol, timeframe)
    
    print(f"✅ Phase 1 complete: {recent_updated} recent rows updated")
    
    # Phase 2: Remaining historical data (2020-2023)
    print("📚 Phase 2: Processing older historical data (2020-2023)...")
    historical_updated = 0
    for symbol, timeframe in combos:
        with engine.connect() as conn:
            historical_updated += historical_backfill(conn, symbol, timeframe)
    
    print(f"✅ Phase 2 complete: {historical_updated} historical rows updated")
    return recent_updated + historical_updated

# ==================== MAIN (TURBO LIVE MODE) ====================
if __name__ == "__main__":
    print("🚀 Start: Miando Indicator Bot TURBO LIVE MODE")
    
    # TURBO LIVE configuration - optimized for live processing
    PROCESSING_MODE = os.getenv('PROCESSING_MODE', 'turbo_live')  # options: 'prioritized', 'standard', 'turbo_live'
    
    try:
        print(f"⚡ Processing mode: {PROCESSING_MODE}")
        
        if PROCESSING_MODE == 'turbo_live':
            print("⚡ TURBO LIVE MODE: Fast live processing with safety limits...")
            
            # Quick backfill with safety limits for recent data only
            with engine.connect() as conn:
                combos = get_symbol_timeframes(conn)
            print(f"📦 TURBO Pairs: {len(combos)} (symbol,timeframe)")

            # Fast backfill for recent gaps only (last 30 days)
            total_hist = 0
            for (symbol, timeframe) in combos:
                print(f"⚡ TURBO Backfill: {symbol} | {timeframe}")
                with engine.connect() as conn:
                    # Quick check for recent nulls only
                    recent_nulls = conn.execute(text(f"""
                        SELECT COUNT(*) FROM ohlc_data 
                        WHERE symbol=:s AND timeframe=:tf 
                        AND open_time >= NOW() - INTERVAL '30 days'
                        AND ({INDICATOR_NULL_PRED})
                    """), {"s": symbol, "tf": timeframe}).scalar()
                    
                    if recent_nulls > 0:
                        print(f"🚀 Processing {recent_nulls} recent gaps for {symbol} {timeframe}")
                        total_hist += historical_backfill(conn, symbol, timeframe)
                    else:
                        print(f"✅ {symbol} {timeframe}: No recent gaps found")
                        
            print(f"🚀 TURBO Backfill complete: {total_hist} rows updated")
            
        elif PROCESSING_MODE == 'prioritized':
            print("🎯 Using prioritized processing (recent data first)...")
            total_hist = prioritized_backfill()
            
        else:  # standard mode with optimized batch sizes
            print("📦 Using standard processing with optimized batch sizes...")
            with engine.connect() as conn:
                combos = get_symbol_timeframes(conn)
            print(f"📦 Pairs: {len(combos)} (symbol,timeframe)")

            total_hist = 0
            for (symbol, timeframe) in combos:
                print(f"⏳ Backfill starting: {symbol} | {timeframe}")
                with engine.connect() as conn:
                    total_hist += historical_backfill(conn, symbol, timeframe)
        
        print(f"✅ Backfill phase complete. Updated Rows: {total_hist}")

        # TURBO Live-Loop (faster polling for live mode)
        live_poll_seconds = 5 if PROCESSING_MODE == 'turbo_live' else POLL_SECONDS
        print(f"🔄 Starting TURBO live loop (polling every {live_poll_seconds}s)")
        
        while True:
            loop_start = time.time()
            loop_upd = 0
            
            with engine.connect() as conn:
                combos = get_symbol_timeframes(conn)
                for (symbol, timeframe) in combos:
                    loop_upd += live_update_once(conn, symbol, timeframe)
                    
            if loop_upd:
                print(f"⚡ TURBO Live-Update: {loop_upd} rows updated in {time.time() - loop_start:.2f}s")
            
            time.sleep(live_poll_seconds)

    except KeyboardInterrupt:
        print("🛑 TURBO mode stopped by user.")
    except Exception as e:
        print(f"❌ TURBO mode error: {e}")
