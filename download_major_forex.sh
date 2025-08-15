#!/bin/bash
# Download 5 years of Dukascopy data for major forex pairs and all standard timeframes
# Output: CSV files in ./download directory

SYMBOLS=(eurusd gbpusd usdjpy usdchf audusd usdcad nzdusd eurjpy gbpjpy audjpy)
TIMEFRAMES=(m1 m5 m15 m30 h1 h4 d1)
START_DATE=2020-01-01
END_DATE=2025-08-12

mkdir -p download

for symbol in "${SYMBOLS[@]}"; do
  for tf in "${TIMEFRAMES[@]}"; do
    out_file="download/${symbol}-${tf}-bid-${START_DATE}-${END_DATE}.csv"
    echo "Downloading $symbol $tf ..."
    dukascopy-node -i "$symbol" -from "$START_DATE" -to "$END_DATE" -t "$tf" -f csv
    # Default output: ${symbol}-${tf}-bid-${START_DATE}-${END_DATE}.csv in current dir
    default_file="${symbol}-${tf}-bid-${START_DATE}-${END_DATE}.csv"
    if [ -f "$default_file" ]; then
      mv "$default_file" "$out_file"
    fi
  done
done
