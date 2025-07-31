#!/usr/bin/env python3
"""
wave.py

Fetch and plot tsunami wave heights from NOAA’s DART buoy network.

Dependencies:
    pip install requests pandas matplotlib

Usage:
    python wave.py
"""

import re
import requests
import pandas as pd
import matplotlib.pyplot as plt


def fetch_dart_data(station_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch tsunami (DART) data from NDBC for station between start_date and end_date.
    Returns a DataFrame indexed by UTC timestamp, with one column 'water_height' (m).
    """
    url = (
        "https://www.ndbc.noaa.gov/dart_data.php"
        f"?station={station_id}&start={start_date}&end={end_date}"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    records = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split()
        # Case A: combined timestamp (YYYYMMDDHHMMSS) + height
        if re.fullmatch(r'\d{14}', parts[0]) and len(parts) >= 2:
            ts = pd.to_datetime(parts[0], format='%Y%m%d%H%M%S', utc=True)
            height = float(parts[1])

        # Case B: split fields YYYY MM DD hh mm ss height …
        elif len(parts) >= 7 and all(re.fullmatch(r'\d+', p) for p in parts[:6]):
            dt_str = ' '.join(parts[0:6])
            ts = pd.to_datetime(dt_str, format='%Y %m %d %H %M %S', utc=True)
            height = float(parts[6])

        else:
            # unexpected format, skip
            continue

        records.append((ts, height))

    if not records:
        raise ValueError(f"No data found for station {station_id}")

    df = pd.DataFrame(records, columns=['datetime', 'water_height']) \
           .set_index('datetime') \
           .sort_index()

    # DROP any duplicate timestamps (keep the first reading)
    df = df[~df.index.duplicated(keep='first')]

    return df


def main():
    # Map of station names to DART station IDs
    stations = {
        'Kamchatka (21416)':     '21416',
        'Tokyo SE (21413)':      '21413',
        'Adak AK (21414)':       '21414',
        'California W (46402)':  '46402',
        'Attu AK (21415)':       '21415',
    }

    # UTC date range (adjust as needed)
    start_date = '2025-07-29'
    end_date   = '2025-07-30'

    dfs = []
    for name, sid in stations.items():
        print(f"Fetching {name} (ID {sid}) from {start_date} to {end_date}…")
        try:
            df = fetch_dart_data(sid, start_date, end_date)
            df = df.rename(columns={'water_height': name})
            dfs.append(df)
        except Exception as e:
            print(f"  ↳ Skipped {sid}: {e}")

    if not dfs:
        print("No data fetched for any station. Exiting.")
        return

    # Combine into a single DataFrame (outer join on UTC index)
    combined = pd.concat(dfs, axis=1)

    # Show the last few rows
    print("\n=== Combined Data Tail ===")
    print(combined.tail())

    # Plotting
    plt.figure(figsize=(10, 6))
    combined.plot(ax=plt.gca())
    plt.title('Tsunami Wave Heights from DART Buoys (m)')
    plt.xlabel('UTC Time')
    plt.ylabel('Water Column Height (m)')
    plt.legend(title='Station')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
