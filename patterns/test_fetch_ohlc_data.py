import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Use the same DB_CONFIG and SYMBOL from your main script
DB_CONFIG = {
    "host": "46.232.249.36",  # Updated to the provided host
    "port": "5434",
    "database": "miando",
    "user": "miando",
    "password": "changeme",  # Added password
    "sslmode": "require",  # Added SSL mode
}

SYMBOL = "XAUUSD"
KERZEN_MENGE = {
    "M1": 5,
    "M5": 30,
    "M15": 16,
    "H1": 20,
    "H4": 6,
    "D1": 4,
}

def fetch_ohlc_data(cur):
    logging.info("Fetching OHLC data...")
    ohlc_data = {}
    last_time = {}
    for tf, limit in KERZEN_MENGE.items():
        logging.info("Querying OHLC data for timeframe: %s with limit: %d", tf, limit)
        cur.execute(
            """
            SELECT open_time, open, high, low, close, volume
            FROM ohlc_data
            WHERE symbol = %s AND timeframe = %s
            ORDER BY open_time DESC LIMIT %s;
            """,
            (SYMBOL, tf, limit)
        )
        rows = cur.fetchall()
        logging.info("Fetched %d rows for timeframe: %s", len(rows), tf)
        if rows:
            ohlc_data[tf] = [dict(r) for r in rows]
            last_time[tf] = rows[0]["open_time"]
    logging.info("OHLC data fetch complete.")
    return ohlc_data, last_time

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            ohlc_data, last_time = fetch_ohlc_data(cur)
            print("OHLC Data:", ohlc_data)
            print("Last Time:", last_time)
    except Exception as e:
        logging.error("Error: %s", e)
    finally:
        if conn:
            conn.close()
