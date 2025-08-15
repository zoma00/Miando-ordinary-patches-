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
CHUNK_ROWS = int(os.getenv('CHUNK_ROWS', '20000'))

# Page size für execute_values (Temp-Table bulk insert)
PAGE_SIZE_VALUES = int(os.getenv('PAGE_SIZE_VALUES', '10000'))

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
    """Ein Batch-Update via temp table & UPDATE JOIN (sehr schnell)."""
    if not rows:
        return 0
    raw = conn.connection  # DBAPI connection (psycopg2)
    with raw.cursor() as cur:
        cur.execute("""
            CREATE TEMP TABLE _ind_upd(
                symbol text, timeframe text, open_time timestamp,
                adx float8, atr float8, bb_upper float8, bb_middle float8, bb_lower float8,
                cci float8, ema float8, macd float8, macd_signal float8, macd_hist float8,
                obv float8, rsi float8, sma float8, stochastic_k float8, stochastic_d float8, willr float8
            ) ON COMMIT DROP;
        """)
        execute_values(cur, "INSERT INTO _ind_upd VALUES %s", rows, page_size=PAGE_SIZE_VALUES)
        cur.execute("""
            UPDATE ohlc_data o
            SET  adx=u.adx, atr=u.atr, bb_upper=u.bb_upper, bb_middle=u.bb_middle, bb_lower=u.bb_lower,
                 cci=u.cci, ema=u.ema, macd=u.macd, macd_signal=u.macd_signal, macd_hist=u.macd_hist,
                 obv=u.obv, rsi=u.rsi, sma=u.sma, stochastic_k=u.stochastic_k, stochastic_d=u.stochastic_d, willr=u.willr
            FROM _ind_upd u
            WHERE o.symbol=u.symbol AND o.timeframe=u.timeframe AND o.open_time=u.open_time
              AND (o.adx IS NULL OR o.atr IS NULL OR o.bb_upper IS NULL OR o.bb_middle IS NULL OR o.bb_lower IS NULL
                   OR o.cci IS NULL OR o.ema IS NULL OR o.macd IS NULL OR o.macd_signal IS NULL OR o.macd_hist IS NULL
                   OR o.obv IS NULL OR o.rsi IS NULL OR o.sma IS NULL OR o.stochastic_k IS NULL OR o.stochastic_d IS NULL OR o.willr IS NULL);
        """)
        updated = cur.rowcount or 0
    return updated

# ==================== Backfill (historisch, schnell) ====================
def historical_backfill(conn, symbol, timeframe):
    """
    Arbeitet Lücken in großen Blöcken ab.
    Für die Berechnung werden stets LOOKBACK_N Kerzen VOR dem Startpunkt genutzt.
    """
    tf_sec = TF_SECONDS.get(timeframe)
    if tf_sec is None:
        print(f"⚠️ Unbekannter TF '{timeframe}' – Backfill übersprungen.")
        return 0

    total_upd = 0
    while True:
        first_null = earliest_null_row(conn, symbol, timeframe)
        if first_null is None:
            break  # alles fertig

        start_ts = first_null - timedelta(seconds=LOOKBACK_N * tf_sec)
        end_ts   = first_null + timedelta(seconds=CHUNK_ROWS * tf_sec)

        df = fetch_range_by_time(conn, symbol, timeframe, start_ts, end_ts)
        if df.empty:
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
            # Nächste Lücke suchen
            break

        with engine.begin() as tx:
            updated = batch_update(tx, rows)
            total_upd += updated
        print(f"⬆️ Backfill {symbol} {timeframe}: +{updated} (bis {df_subset['open_time'].max()})")

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

    with engine.begin() as tx:
        updated = batch_update(tx, rows)
    return updated

# ==================== MAIN ====================
if __name__ == "__main__":
    print("🚀 Start: Miando Indicator Bot (Backfill + Live 15s)")
    try:
        # 1) Historischer Backfill (schnell, in Blöcken)
        with engine.connect() as conn:
            combos = get_symbol_timeframes(conn)
        print(f"📦 Paare: {len(combos)} (symbol,timeframe)")

        total_hist = 0
        for (symbol, timeframe) in combos:
            print(f"⏳ Backfill startet: {symbol} | {timeframe}")
            with engine.connect() as conn:
                total_hist += historical_backfill(conn, symbol, timeframe)
        print(f"✅ Backfill fertig. Updated Rows: {total_hist}")

        # 2) Live-Loop (alle 15s)
        while True:
            loop_upd = 0
            with engine.connect() as conn:
                combos = get_symbol_timeframes(conn)
                for (symbol, timeframe) in combos:
                    loop_upd += live_update_once(conn, symbol, timeframe)
            if loop_upd:
                print(f"🔄 Live-Update: {loop_upd} Zeilen aktualisiert")
            time.sleep(POLL_SECONDS)

    except KeyboardInterrupt:
        print("🛑 Beendet durch Benutzer.")
    except Exception as e:
        print(f"❌ Fehler: {e}")