#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Linux-Version: JSON-Exporter für Miando V3 – Full-Profit Mode
Speichert regelmäßig den vollständigen Snapshot zur Analyse durch GPT.
"""

from __future__ import annotations
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# ===================== KONFIGURATION =====================

B_CONFIG = {
    "host": "miando-db",      # ✅ Docker service name
    "port": "5432",
    "database": "miando",     # ✅ Correct database name
    "user": "miando",
    "password": "changeme",
    # Optional für SSL:
    # "sslmode": "require",
    # "sslrootcert": "/etc/ssl/certs/server.crt",
}

EXPORT_FILE = "/opt/miando/data/trading_snapshot_gold.json"
CLOSED_TRADES_FILE = "/opt/miando/data/closed_trades.json"
LOG_FILE = "/opt/miando/logs/json_exporter.log"
SYMBOL = "XAUUSD"

KERZEN_MENGE: Dict[str, int] = {
    "M1": 5,
    "M5": 30,
    "M15": 16,
    "H1": 20,
    "H4": 6,
    "D1": 4,
}

DAILY_LOSS_LIMIT_PCT = 6.0

BROKER_INFO = {
    "name": "Fusion Markets",
    "min_stop": 0.0,
    "commission_per_lot": 4.0,
    "commission_currency": "USD",
    "commission_model": "per_lot",
}

# ===================== LOGGING =====================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ========== (ALLE FUNKTIONEN AUS DEINEM OBENEN CODE HIER EINFÜGEN) ==========
# Für bessere Übersicht ausgelassen, da du sie oben bereits vollständig gepostet hast.
# → Einfach deinen gesamten Funktionscode (fetch_*, get_day_open_state, write_snapshot, etc.)
#    direkt hier einfügen – KEINE Änderungen nötig, außer ggf. DB_CONFIG und Pfade.
# ============================================================================

# Beispielhafte letzte Funktion (wie oben):
def write_snapshot():
    conn = None
    try:
        conn = open_pg_conn()
        with with_cursor(conn) as cur:
            account_id = fetch_latest_account_id(cur)
            if not account_id:
                logging.warning("Kein account_id gefunden.")
                return

            ohlc_data, last_time = fetch_ohlc_data(cur)
            if "M1" not in last_time:
                logging.warning("Keine M1-Daten verfügbar.")
                return

            ref_time_utc = datetime.fromisoformat(str(last_time["M1"]))
            if ref_time_utc.tzinfo is None:
                ref_time_utc = ref_time_utc.replace(tzinfo=timezone.utc)
            else:
                ref_time_utc = ref_time_utc.astimezone(timezone.utc)

            snapshot = {
                "symbol": SYMBOL,
                "account_id": account_id,
                "timestamp": ref_time_utc.isoformat(),
                "ohlc": ohlc_data,
                "ohlc_last_time": last_time,
                "account_state": fetch_account_state(cur, account_id),
                "market_state": market_state(ohlc_data.get("M1", []), ref_time_utc),
                "daily_stats": daily_stats(cur, account_id),
                "recent_losses": fetch_recent_losses(),
                "trades": fetch_trades(cur, account_id),
                "broker": BROKER_INFO,
                "limits": {
                    "daily_loss_limit_pct": DAILY_LOSS_LIMIT_PCT
                }
            }

            # Save JSON snapshot to file
            Path(EXPORT_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(EXPORT_FILE, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)

            logging.info("Snapshot geschrieben: %s", EXPORT_FILE)

            # Save JSON snapshot to database for all timeframes
            table_name = "ohlc_eurusd" if SYMBOL.upper() == "EURUSD" else "ohlc_xauusd" if SYMBOL.upper() == "XAUUSD" else "ohlc_eurusd"
            for timeframe, open_time in last_time.items():
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET snapshot = %s
                    WHERE symbol = %s AND timeframe = %s AND open_time = %s
                    """,
                    (json.dumps(snapshot), SYMBOL, timeframe, open_time)
                )

            logging.info("Snapshot in Datenbank gespeichert für alle Timeframes.")

    except Exception as e:
        logging.error("Fehler beim Snapshot: %s", e)
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

# ===================== MAIN LOOP =====================

if __name__ == "__main__":
    logging.info("Starte JSON-Exporter für Miando...")
    while True:
        write_snapshot()
        time.sleep(60)
