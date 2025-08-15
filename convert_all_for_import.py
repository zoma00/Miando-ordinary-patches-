import csv
import os
import datetime

INPUT_DIR = 'download'
OUTPUT_SUFFIX = '-for-import.csv'
VOLUME_DEFAULT = 0

def parse_symbol_timeframe(filename):
    # Example: eurusd-m1-bid-2020-01-01-2025-08-12.csv
    parts = filename.split('-')
    if len(parts) < 5:
        return None, None
    symbol = parts[0].upper()
    timeframe = parts[1].upper()
    return symbol, timeframe

def convert_file(input_path, output_path, symbol, timeframe):
    with open(input_path, 'r', newline='') as infile, open(output_path, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        required_fields = {'timestamp', 'open', 'high', 'low', 'close'}
        if not reader.fieldnames or not required_fields.issubset(set(reader.fieldnames)):
            missing = required_fields - set(reader.fieldnames) if reader.fieldnames else required_fields
            print(f"Skipping {os.path.basename(input_path)}: missing required columns {missing}")
            return
        fieldnames = [
            'symbol', 'timeframe', 'open_time', 'open_price', 'high_price', 'low_price', 'close_price', 'volume'
        ]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            ts = int(row['timestamp'])
            open_time = datetime.datetime.utcfromtimestamp(ts // 1000).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow({
                'symbol': symbol,
                'timeframe': timeframe,
                'open_time': open_time,
                'open_price': row['open'],
                'high_price': row['high'],
                'low_price': row['low'],
                'close_price': row['close'],
                'volume': VOLUME_DEFAULT
            })

for fname in os.listdir(INPUT_DIR):
    if not fname.endswith('.csv') or fname.endswith(OUTPUT_SUFFIX):
        continue
    symbol, timeframe = parse_symbol_timeframe(fname)
    if not symbol or not timeframe:
        print(f"Skipping {fname}: can't parse symbol/timeframe")
        continue
    input_path = os.path.join(INPUT_DIR, fname)
    output_path = os.path.join(INPUT_DIR, fname.replace('.csv', OUTPUT_SUFFIX))
    print(f"Converting {fname} -> {os.path.basename(output_path)} ...")
    convert_file(input_path, output_path, symbol, timeframe)
print("All files converted.")
