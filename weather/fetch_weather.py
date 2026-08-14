"""
Fetch 20 years of historical hourly weather data (June 11-27) for each
2026 FIFA World Cup venue, then average across years to produce predicted
weather for the 2026 group stage.

Data source: Open-Meteo Historical Weather API (coordinate-based, free, no key)
Variables: temperature_2m, relative_humidity_2m (hourly, 10:00-22:00 local)
"""

import csv
import time
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENUES_CSV = os.path.join(SCRIPT_DIR, "venues.csv")
RAW_CSV = os.path.join(SCRIPT_DIR, "venue_weather_hourly_raw.csv")
FINAL_CSV = os.path.join(SCRIPT_DIR, "venue_weather_hourly_predicted.csv")

START_MMDD = (6, 11)
END_MMDD = (6, 27)
HOURS_LOCAL = list(range(10, 23))  # 10:00 through 22:00 inclusive
YEAR_START = 2005
YEAR_END = 2024
NUM_YEARS = YEAR_END - YEAR_START + 1

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def load_venues(path):
    venues = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            venues.append({
                "venue_id": int(row["venue_id"]),
                "city": row["city"],
                "latitude": float(row["venue_latitude"]),
                "longitude": float(row["venue_longitude"]),
                "timezone": row["iana_timezone"],
                "utc_offset": int(row["utc_offset"]),
            })
    return venues


def fetch_year(lat, lon, year, timezone):
    """Fetch hourly temp + humidity for June 11-27 of a given year."""
    start = f"{year}-{START_MMDD[0]:02d}-{START_MMDD[1]:02d}"
    end = f"{year}-{END_MMDD[0]:02d}-{END_MMDD[1]:02d}"
    params = (
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={end}"
        f"&hourly=temperature_2m,relative_humidity_2m"
        f"&timezone={timezone}"
    )
    url = f"{BASE_URL}?{params}"

    for attempt in range(3):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
    return None


def parse_hourly(data, venue_id, city, year):
    """Extract rows for hours 10-22 from the API response."""
    rows = []
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humids = hourly.get("relative_humidity_2m", [])

    for i, ts in enumerate(times):
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M")
        if dt.hour in HOURS_LOCAL:
            rows.append({
                "venue_id": venue_id,
                "city": city,
                "year": year,
                "date_mmdd": dt.strftime("%m-%d"),
                "hour_local": dt.hour,
                "temperature_c": temps[i] if i < len(temps) else None,
                "humidity_pct": humids[i] if i < len(humids) else None,
            })
    return rows


def write_raw(all_rows, path):
    fieldnames = ["venue_id", "city", "year", "date_mmdd", "hour_local",
                  "temperature_c", "humidity_pct"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Raw data written: {len(all_rows)} rows -> {path}")


def compute_averages(raw_rows):
    """Average temperature and humidity across years for each venue-date-hour."""
    buckets = {}
    for r in raw_rows:
        key = (r["venue_id"], r["city"], r["date_mmdd"], r["hour_local"])
        if key not in buckets:
            buckets[key] = {"temps": [], "humids": []}
        if r["temperature_c"] is not None:
            buckets[key]["temps"].append(float(r["temperature_c"]))
        if r["humidity_pct"] is not None:
            buckets[key]["humids"].append(float(r["humidity_pct"]))

    final = []
    for (venue_id, city, date_mmdd, hour_local), vals in sorted(buckets.items()):
        avg_temp = round(sum(vals["temps"]) / len(vals["temps"]), 1) if vals["temps"] else None
        avg_humid = round(sum(vals["humids"]) / len(vals["humids"]), 1) if vals["humids"] else None
        final.append({
            "venue_id": venue_id,
            "city": city,
            "date": f"2026-{date_mmdd}",
            "hour_local": hour_local,
            "base_temperature_c": avg_temp,
            "humidity_pct": avg_humid,
            "source_id": f"open-meteo-{NUM_YEARS}yr-avg",
        })
    return final


def write_final(final_rows, path):
    fieldnames = ["venue_id", "city", "date", "hour_local",
                  "base_temperature_c", "humidity_pct", "source_id"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)
    print(f"Final predictions written: {len(final_rows)} rows -> {path}")


def main():
    venues = load_venues(VENUES_CSV)
    print(f"Loaded {len(venues)} venues")
    print(f"Fetching {NUM_YEARS} years ({YEAR_START}-{YEAR_END}) x {len(venues)} venues")
    print(f"Dates: June {START_MMDD[1]}-{END_MMDD[1]}, Hours: {HOURS_LOCAL[0]}:00-{HOURS_LOCAL[-1]}:00 local\n")

    all_raw = []
    total_calls = NUM_YEARS * len(venues)
    call_num = 0

    for venue in venues:
        print(f"[{venue['venue_id']:2d}/16] {venue['city']} ({venue['latitude']}, {venue['longitude']})")
        for year in range(YEAR_START, YEAR_END + 1):
            call_num += 1
            data = fetch_year(venue["latitude"], venue["longitude"], year, venue["timezone"])
            if data is None:
                print(f"  FAILED: {year}")
                continue

            rows = parse_hourly(data, venue["venue_id"], venue["city"], year)
            all_raw.extend(rows)

            if call_num % 20 == 0:
                print(f"  Progress: {call_num}/{total_calls} API calls done")

            time.sleep(0.3)

        print(f"  Done — {len([r for r in all_raw if r['venue_id'] == venue['venue_id']])} raw rows\n")

    write_raw(all_raw, RAW_CSV)

    final = compute_averages(all_raw)
    write_final(final, FINAL_CSV)

    print("\nComplete!")
    print(f"  Raw:   {RAW_CSV}")
    print(f"  Final: {FINAL_CSV}")


if __name__ == "__main__":
    main()
