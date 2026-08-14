"""
Aggregate country-level timezone population data into a regional summary
for the FIFA World Cup 2026 viewership model.

INPUT:  country_timezone_reference.csv  (223 rows — one per country or sub-country zone)
OUTPUT: timezone_population.csv         (46 rows  — one per region + UTC offset)

Aggregation: sums population_millions by (fifa_audience_region, utc_offset_june),
then attaches regional_population (sum across all offsets in that region) and
regional_viewership from FIFA's Qatar 2022 Total Engagement figures.

SOURCES (numbered keys match the 'source' column in country_timezone_reference.csv):
  [1] UN World Population Prospects 2024 Revision — https://population.un.org/wpp/
  [2] US Census Bureau state estimates 2024 — https://www.census.gov/data/tables/time-series/demo/popest/2020s-state-total.html
  [3] Statistics Canada provincial estimates 2024 — https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000901
  [4] IBGE Brazil state estimates 2024 — https://www.ibge.gov.br/estatisticas/sociais/populacao.html
  [5] BPS Indonesia provincial census 2020 (projected 2025) — https://www.bps.go.id/
  [6] ABS Australia state estimates 2024 — https://www.abs.gov.au/statistics/people/population
  [7] INEGI Mexico state census 2020 (projected 2025) — https://www.inegi.org.mx/
  [8] Rosstat Russia federal subject population 2024 — https://rosstat.gov.ru/
  [9] FIFA/Nielsen Qatar 2022 Global Viewership Report (Total Engagement by region)
"""

import csv
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, "country_timezone_reference.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "timezone_population.csv")

REGIONAL_VIEWERSHIP = {
    "Asia & Oceania": 2591,
    "Africa & Middle East": 945,
    "Europe": 522,
    "North Central America & Caribbean": 369,
    "South America": 365,
}


def format_offset(offset):
    if offset == 0:
        return "UTC+0"
    sign = "+" if offset > 0 else "-"
    abs_offset = abs(offset)
    hours = int(abs_offset)
    minutes = int((abs_offset - hours) * 60)
    if minutes:
        return f"UTC{sign}{hours}:{minutes:02d}"
    return f"UTC{sign}{hours}"


def main():
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"Loaded {len(rows)} country entries from {INPUT_CSV}")

    tz_pop = defaultdict(float)
    for row in rows:
        region = row["fifa_audience_region"]
        offset = float(row["utc_offset_june"])
        pop = float(row["population_millions"])
        tz_pop[(region, offset)] += pop

    reg_pop = defaultdict(float)
    for (region, offset), pop in tz_pop.items():
        reg_pop[region] += pop

    output = []
    for (region, offset), pop in sorted(tz_pop.items(), key=lambda x: (x[0][0], x[0][1])):
        output.append({
            "audience_region": region,
            "utc_offset": format_offset(offset),
            "timezone_population": round(pop, 1),
            "regional_population": round(reg_pop[region], 1),
            "regional_viewership": REGIONAL_VIEWERSHIP.get(region, ""),
        })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "audience_region", "utc_offset", "timezone_population",
            "regional_population", "regional_viewership"])
        writer.writeheader()
        writer.writerows(output)

    print(f"\nRegion summary:")
    seen = set()
    for r in output:
        reg = r["audience_region"]
        if reg not in seen:
            n = sum(1 for x in output if x["audience_region"] == reg)
            print(f"  {reg}: {r['regional_population']}M across {n} UTC offsets")
            seen.add(reg)

    print(f"\nWritten {len(output)} rows -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
