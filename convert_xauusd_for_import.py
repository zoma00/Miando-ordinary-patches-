import csv
import datetime

INPUT_CSV = 'download/xauusd-m1-bid-2020-01-01-2025-08-12.csv'
OUTPUT_CSV = 'download/xauusd-m1-for-import.csv'

SYMBOL = 'XAUUSD'
TIMEFRAME = 'M1'
VOLUME = 0

with open(INPUT_CSV, 'r', newline='') as infile, open(OUTPUT_CSV, 'w', newline='') as outfile:
    reader = csv.DictReader(infile)
    fieldnames = [
        'symbol', 'timeframe', 'open_time', 'open_price', 'high_price', 'low_price', 'close_price', 'volume'
    ]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in reader:
        # Convert open_time from ms to ISO timestamp
        ts = int(row['open_time'])
        open_time = datetime.datetime.utcfromtimestamp(ts // 1000).strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow({
            'symbol': SYMBOL,
            'timeframe': TIMEFRAME,
            'open_time': open_time,
            'open_price': row['open'],
            'high_price': row['high'],
            'low_price': row['low'],
            'close_price': row['close'],
            'volume': VOLUME
        })
print(f"Done. Output: {OUTPUT_CSV}")
