#!/bin/bash
# Batch import all *-for-import.csv files into PostgreSQL via Docker
# Usage: bash import_all_ohlc_data.sh

set -e

CONTAINER=miando-db
DB=miando
USER=miando
DATA_DIR=download

# 1. Truncate the ohlc_data table

echo "Truncating ohlc_data table..."
docker exec -i $CONTAINER psql -U $USER -d $DB -c "TRUNCATE ohlc_data;"

echo "Copying CSV files into container..."
for f in $DATA_DIR/*-for-import.csv; do
    [ -e "$f" ] || continue
    docker cp "$f" $CONTAINER:/tmp/$(basename "$f")
done

echo "Importing CSV files into ohlc_data..."
for f in $DATA_DIR/*-for-import.csv; do
    [ -e "$f" ] || continue
    fname=$(basename "$f")
    docker exec -i $CONTAINER psql -U $USER -d $DB -c \
        "\copy ohlc_data(symbol, timeframe, open_time, open_price, high_price, low_price, close_price, volume) FROM '/tmp/$fname' DELIMITER ',' CSV HEADER;"
done

echo "Cleaning up CSV files from container..."
for f in $DATA_DIR/*-for-import.csv; do
    [ -e "$f" ] || continue
    fname=$(basename "$f")
    docker exec -i $CONTAINER rm -f /tmp/$fname
done

echo "All files imported successfully."
