"""
Build timezone population table for FIFA World Cup 2026 viewership model.

Maps every country to its FIFA audience region and June UTC offset,
then aggregates population by region + offset.

For multi-zone countries (USA, Canada, Brazil, Indonesia, Australia, Mexico, Russia),
population is split at the state/provincial level using census data.

OUTPUT: timezone_population.csv
COLUMNS: audience_region, utc_offset, timezone_population, regional_population, regional_viewership

SOURCES:
--------
[1] UN World Population Prospects 2024 Revision — country-level estimates for 2025
    https://population.un.org/wpp/

[2] US Census Bureau — state population estimates 2024
    https://www.census.gov/data/tables/time-series/demo/popest/2020s-state-total.html

[3] Statistics Canada — provincial population estimates 2024
    https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000901

[4] IBGE (Brazil) — state population estimates 2024
    https://www.ibge.gov.br/estatisticas/sociais/populacao.html

[5] BPS (Indonesia) — provincial population census 2020, projected 2025
    https://www.bps.go.id/

[6] ABS (Australia) — state population estimates 2024
    https://www.abs.gov.au/statistics/people/population

[7] INEGI (Mexico) — state population census 2020, projected 2025
    https://www.inegi.org.mx/

[8] Rosstat (Russia) — federal subject population 2024
    https://rosstat.gov.ru/

[9] FIFA World Cup Qatar 2022 Global Viewership Report (Nielsen/PSE)
    Total Engagement by region — used for regional_viewership column

UTC offsets are for JUNE (Northern Hemisphere summer / Southern Hemisphere winter),
accounting for Daylight Saving Time where applicable.
"""

import csv
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "timezone_population.csv")

# FIFA 2022 Total Engagement by region (millions) — from Nielsen report slide 7
REGIONAL_VIEWERSHIP = {
    "Asia & Oceania": 2591,
    "Africa & Middle East": 945,
    "Europe": 522,
    "North, Central America & Caribbean": 369,
    "South America": 365,
}

# ============================================================================
# COUNTRY DATA: (country, fifa_region, utc_offset_june, population_millions)
#
# Population figures: UN WPP 2024 mid-year estimates for 2025 (rounded)
# UTC offsets: June values (DST-adjusted where applicable)
# Half-hour offsets stored as floats (e.g., +5.5 for India)
#
# Multi-zone countries are split into sub-entries by state/province group.
# ============================================================================

COUNTRY_DATA = [
    # =========================================================================
    # ASIA & OCEANIA
    # =========================================================================

    # --- South Asia ---
    ("India", "Asia & Oceania", 5.5, 1450),
    ("Pakistan", "Asia & Oceania", 5, 240),
    ("Bangladesh", "Asia & Oceania", 6, 175),
    ("Nepal", "Asia & Oceania", 5.75, 31),
    ("Sri Lanka", "Asia & Oceania", 5.5, 22),
    ("Afghanistan", "Asia & Oceania", 4.5, 42),
    ("Maldives", "Asia & Oceania", 5, 0.5),
    ("Bhutan", "Asia & Oceania", 6, 0.8),

    # --- East Asia ---
    ("China", "Asia & Oceania", 8, 1410),
    ("Japan", "Asia & Oceania", 9, 124),
    ("South Korea", "Asia & Oceania", 9, 52),
    ("North Korea", "Asia & Oceania", 9, 26),
    ("Mongolia", "Asia & Oceania", 8, 3.4),
    ("Taiwan", "Asia & Oceania", 8, 24),
    ("Hong Kong", "Asia & Oceania", 8, 7.5),
    ("Macau", "Asia & Oceania", 8, 0.7),

    # --- Southeast Asia ---
    # Indonesia split by timezone zone [5]:
    #   WIB (Java, Sumatra, West/Central Kalimantan): UTC+7, ~225M
    #   WITA (Bali, East/South Kalimantan, Sulawesi, NTT, NTB): UTC+8, ~37M
    #   WIT (Papua, Maluku): UTC+9, ~7M
    ("Indonesia WIB (Java/Sumatra)", "Asia & Oceania", 7, 225),
    ("Indonesia WITA (Bali/Kalimantan/Sulawesi)", "Asia & Oceania", 8, 37),
    ("Indonesia WIT (Papua/Maluku)", "Asia & Oceania", 9, 7),
    ("Philippines", "Asia & Oceania", 8, 117),
    ("Vietnam", "Asia & Oceania", 7, 100),
    ("Thailand", "Asia & Oceania", 7, 72),
    ("Myanmar", "Asia & Oceania", 6.5, 55),
    ("Malaysia", "Asia & Oceania", 8, 34),
    ("Cambodia", "Asia & Oceania", 7, 17),
    ("Laos", "Asia & Oceania", 7, 8),
    ("Singapore", "Asia & Oceania", 8, 6),
    ("Timor-Leste", "Asia & Oceania", 9, 1.4),
    ("Brunei", "Asia & Oceania", 8, 0.5),

    # --- Central Asia (AFC-affiliated or geographically Asian) ---
    ("Uzbekistan", "Asia & Oceania", 5, 35),
    ("Tajikistan", "Asia & Oceania", 5, 10),
    ("Kyrgyzstan", "Asia & Oceania", 6, 7),
    ("Turkmenistan", "Asia & Oceania", 5, 6.5),

    # --- Caucasus (AFC/UEFA border — counted here as Asia for FIFA viewership) ---
    ("Georgia", "Asia & Oceania", 4, 3.7),
    ("Armenia", "Asia & Oceania", 4, 3),
    ("Azerbaijan", "Asia & Oceania", 4, 10.3),

    # --- Iran (AFC member) ---
    ("Iran", "Asia & Oceania", 3.5, 89),

    # --- Oceania ---
    # Australia split by state [6]:
    #   Eastern (NSW, VIC, QLD, TAS, ACT): UTC+10 in June (AEST, no DST)
    #   Central (SA, NT): UTC+9.5 in June
    #   Western (WA): UTC+8
    ("Australia Eastern (NSW/VIC/QLD/TAS/ACT)", "Asia & Oceania", 10, 20.5),
    ("Australia Central (SA/NT)", "Asia & Oceania", 9.5, 2.1),
    ("Australia Western (WA)", "Asia & Oceania", 8, 2.9),
    ("New Zealand", "Asia & Oceania", 12, 5.2),
    ("Papua New Guinea", "Asia & Oceania", 10, 10),
    ("Fiji", "Asia & Oceania", 12, 0.9),
    ("Solomon Islands", "Asia & Oceania", 11, 0.7),
    ("Vanuatu", "Asia & Oceania", 11, 0.3),
    ("New Caledonia", "Asia & Oceania", 11, 0.3),
    ("Samoa", "Asia & Oceania", 13, 0.2),
    ("Tonga", "Asia & Oceania", 13, 0.1),

    # =========================================================================
    # AFRICA & MIDDLE EAST
    # =========================================================================

    # --- Middle East (grouped with Africa in FIFA viewership report) ---
    ("Saudi Arabia", "Africa & Middle East", 3, 37),
    ("Iraq", "Africa & Middle East", 3, 44),
    ("Yemen", "Africa & Middle East", 3, 34),
    ("Jordan", "Africa & Middle East", 3, 11.5),
    ("UAE", "Africa & Middle East", 4, 10),
    ("Kuwait", "Africa & Middle East", 3, 4.5),
    ("Oman", "Africa & Middle East", 4, 4.7),
    ("Qatar", "Africa & Middle East", 3, 2.7),
    ("Bahrain", "Africa & Middle East", 3, 1.6),
    ("Lebanon", "Africa & Middle East", 3, 5.5),
    ("Palestine", "Africa & Middle East", 3, 5.5),
    ("Syria", "Africa & Middle East", 3, 23),

    # --- North Africa ---
    ("Egypt", "Africa & Middle East", 2, 106),
    ("Algeria", "Africa & Middle East", 1, 46),
    ("Morocco", "Africa & Middle East", 1, 38),
    ("Tunisia", "Africa & Middle East", 1, 12.5),
    ("Libya", "Africa & Middle East", 2, 7),
    ("Sudan", "Africa & Middle East", 2, 48),
    ("South Sudan", "Africa & Middle East", 2, 12),

    # --- West Africa ---
    ("Nigeria", "Africa & Middle East", 1, 230),
    ("Ghana", "Africa & Middle East", 0, 34),
    ("Ivory Coast", "Africa & Middle East", 0, 29),
    ("Niger", "Africa & Middle East", 1, 27),
    ("Mali", "Africa & Middle East", 0, 23),
    ("Burkina Faso", "Africa & Middle East", 0, 23),
    ("Senegal", "Africa & Middle East", 0, 18),
    ("Guinea", "Africa & Middle East", 0, 14.5),
    ("Benin", "Africa & Middle East", 1, 13.5),
    ("Togo", "Africa & Middle East", 0, 9),
    ("Sierra Leone", "Africa & Middle East", 0, 8.5),
    ("Liberia", "Africa & Middle East", 0, 5.5),
    ("Mauritania", "Africa & Middle East", 0, 5),
    ("Gambia", "Africa & Middle East", 0, 2.7),
    ("Guinea-Bissau", "Africa & Middle East", 0, 2.2),
    ("Cabo Verde", "Africa & Middle East", -1, 0.6),

    # --- Central Africa ---
    ("DRC", "Africa & Middle East", 2, 105),
    ("Cameroon", "Africa & Middle East", 1, 29),
    ("Angola", "Africa & Middle East", 1, 37),
    ("Chad", "Africa & Middle East", 1, 18.5),
    ("Central African Republic", "Africa & Middle East", 1, 5.5),
    ("Republic of Congo", "Africa & Middle East", 1, 6),
    ("Gabon", "Africa & Middle East", 1, 2.5),
    ("Equatorial Guinea", "Africa & Middle East", 1, 1.7),
    ("Sao Tome and Principe", "Africa & Middle East", 0, 0.2),

    # --- East Africa ---
    ("Ethiopia", "Africa & Middle East", 3, 130),
    ("Kenya", "Africa & Middle East", 3, 56),
    ("Tanzania", "Africa & Middle East", 3, 67),
    ("Uganda", "Africa & Middle East", 3, 50),
    ("Mozambique", "Africa & Middle East", 2, 34),
    ("Madagascar", "Africa & Middle East", 3, 30),
    ("Somalia", "Africa & Middle East", 3, 18),
    ("Rwanda", "Africa & Middle East", 2, 14),
    ("Burundi", "Africa & Middle East", 2, 13.5),
    ("Eritrea", "Africa & Middle East", 3, 3.7),
    ("Djibouti", "Africa & Middle East", 3, 1.1),
    ("Comoros", "Africa & Middle East", 3, 1),
    ("Mauritius", "Africa & Middle East", 4, 1.3),
    ("Seychelles", "Africa & Middle East", 4, 0.1),

    # --- Southern Africa ---
    ("South Africa", "Africa & Middle East", 2, 60),
    ("Zimbabwe", "Africa & Middle East", 2, 16.5),
    ("Zambia", "Africa & Middle East", 2, 20.5),
    ("Malawi", "Africa & Middle East", 2, 21),
    ("Namibia", "Africa & Middle East", 2, 2.7),
    ("Botswana", "Africa & Middle East", 2, 2.5),
    ("Lesotho", "Africa & Middle East", 2, 2.3),
    ("Eswatini", "Africa & Middle East", 2, 1.2),

    # =========================================================================
    # EUROPE (UEFA members — June DST offsets)
    # =========================================================================

    # UTC+1 in June (BST / WEST)
    ("United Kingdom", "Europe", 1, 68),
    ("Ireland", "Europe", 1, 5.2),
    ("Portugal", "Europe", 1, 10.4),
    ("Iceland", "Europe", 0, 0.4),

    # UTC+2 in June (CEST)
    ("Germany", "Europe", 2, 84),
    ("France", "Europe", 2, 66),
    ("Italy", "Europe", 2, 59),
    ("Spain", "Europe", 2, 48),
    ("Poland", "Europe", 2, 37),
    ("Netherlands", "Europe", 2, 18),
    ("Belgium", "Europe", 2, 11.7),
    ("Czech Republic", "Europe", 2, 10.9),
    ("Sweden", "Europe", 2, 10.5),
    ("Hungary", "Europe", 2, 10),
    ("Austria", "Europe", 2, 9.2),
    ("Switzerland", "Europe", 2, 8.9),
    ("Serbia", "Europe", 2, 6.6),
    ("Denmark", "Europe", 2, 5.9),
    ("Norway", "Europe", 2, 5.5),
    ("Slovakia", "Europe", 2, 5.4),
    ("Croatia", "Europe", 2, 3.9),
    ("Bosnia and Herzegovina", "Europe", 2, 3.2),
    ("Albania", "Europe", 2, 2.8),
    ("Slovenia", "Europe", 2, 2.1),
    ("North Macedonia", "Europe", 2, 1.8),
    ("Kosovo", "Europe", 2, 1.8),
    ("Montenegro", "Europe", 2, 0.6),
    ("Luxembourg", "Europe", 2, 0.7),
    ("Malta", "Europe", 2, 0.5),
    ("Andorra", "Europe", 2, 0.08),
    ("Liechtenstein", "Europe", 2, 0.04),
    ("San Marino", "Europe", 2, 0.03),

    # UTC+3 in June (EEST / permanent for Turkey)
    ("Turkey", "Europe", 3, 86),
    ("Ukraine", "Europe", 3, 37),
    ("Romania", "Europe", 3, 19),
    ("Greece", "Europe", 3, 10.3),
    ("Finland", "Europe", 3, 5.6),
    ("Bulgaria", "Europe", 3, 6.5),
    ("Lithuania", "Europe", 3, 2.8),
    ("Latvia", "Europe", 3, 1.8),
    ("Estonia", "Europe", 3, 1.4),
    ("Cyprus", "Europe", 3, 1.3),
    ("Moldova", "Europe", 3, 2.6),

    # Russia split by federal subject groups [8]:
    #   Moscow/Western Russia (UTC+3): ~105M
    #   Samara/Udmurtia (UTC+4): ~15M
    #   Yekaterinburg zone (UTC+5): ~20M
    #   Omsk zone (UTC+6): ~8M
    #   Krasnoyarsk zone (UTC+7): ~8M
    #   Irkutsk zone (UTC+8): ~5M
    #   Yakutsk zone (UTC+9): ~3M
    #   Vladivostok zone (UTC+10): ~4M
    #   Magadan/Sakhalin (UTC+11): ~1.5M
    #   Kamchatka (UTC+12): ~0.5M
    ("Russia UTC+3 (Moscow/West)", "Europe", 3, 105),
    ("Russia UTC+4 (Samara)", "Europe", 4, 15),
    ("Russia UTC+5 (Yekaterinburg)", "Europe", 5, 20),
    ("Russia UTC+6 (Omsk)", "Europe", 6, 8),
    ("Russia UTC+7 (Krasnoyarsk)", "Europe", 7, 8),
    ("Russia UTC+8 (Irkutsk)", "Europe", 8, 5),
    ("Russia UTC+9 (Yakutsk)", "Europe", 9, 3),
    ("Russia UTC+10 (Vladivostok)", "Europe", 10, 4),
    ("Russia UTC+11 (Magadan)", "Europe", 11, 1.5),
    ("Russia UTC+12 (Kamchatka)", "Europe", 12, 0.5),

    # Belarus (permanent UTC+3)
    ("Belarus", "Europe", 3, 9.2),

    # Israel (UEFA member, UTC+3 in June DST)
    ("Israel", "Europe", 3, 9.9),

    # Kazakhstan (UEFA member for football)
    # Split: Western (UTC+5) ~5M, Eastern (UTC+6) ~14M
    ("Kazakhstan West", "Europe", 5, 5),
    ("Kazakhstan East", "Europe", 6, 14),

    # Faroe Islands, Gibraltar, etc. (negligible)

    # =========================================================================
    # NORTH, CENTRAL AMERICA & CARIBBEAN (CONCACAF)
    # =========================================================================

    # USA split by timezone [2]:
    #   Eastern (UTC-4 June): ~152M
    #   Central (UTC-5 June): ~95M
    #   Mountain excl AZ (UTC-6 June): ~18M
    #   Pacific + Arizona (UTC-7 June): ~60M
    #   Alaska (UTC-8 June): ~0.7M
    #   Hawaii (UTC-10): ~1.5M
    ("USA Eastern", "North, Central America & Caribbean", -4, 152),
    ("USA Central", "North, Central America & Caribbean", -5, 95),
    ("USA Mountain", "North, Central America & Caribbean", -6, 18),
    ("USA Pacific + Arizona", "North, Central America & Caribbean", -7, 60),
    ("USA Alaska", "North, Central America & Caribbean", -8, 0.7),
    ("USA Hawaii", "North, Central America & Caribbean", -10, 1.5),

    # Canada split by province [3]:
    #   Atlantic (UTC-3 June): NB, NS, PEI ~2M
    #   Newfoundland (UTC-2.5 June): ~0.5M
    #   Eastern (UTC-4 June): ON, QC ~23M
    #   Central (UTC-5 June): MB, SK ~2.5M
    #   Mountain (UTC-6 June): AB ~4.7M
    #   Pacific (UTC-7 June): BC ~5.4M
    ("Canada Atlantic", "North, Central America & Caribbean", -3, 2),
    ("Canada Newfoundland", "North, Central America & Caribbean", -2.5, 0.5),
    ("Canada Eastern (ON/QC)", "North, Central America & Caribbean", -4, 23),
    ("Canada Central (MB/SK)", "North, Central America & Caribbean", -5, 2.5),
    ("Canada Mountain (AB)", "North, Central America & Caribbean", -6, 4.7),
    ("Canada Pacific (BC)", "North, Central America & Caribbean", -7, 5.4),

    # Mexico split [7]:
    #   Most of Mexico (UTC-6 year-round after 2022 DST abolition): ~125M
    #   Sonora (UTC-7, no DST same as US Pacific): ~3.1M
    #   Quintana Roo (UTC-5, Eastern Standard permanent): ~1.9M
    #   Baja California (UTC-7 June, follows US Pacific DST): ~3.8M
    ("Mexico Central/Most (no DST since 2022)", "North, Central America & Caribbean", -6, 125),
    ("Mexico Sonora", "North, Central America & Caribbean", -7, 3.1),
    ("Mexico Baja California", "North, Central America & Caribbean", -7, 3.8),
    ("Mexico Quintana Roo", "North, Central America & Caribbean", -5, 1.9),

    # Central America
    ("Guatemala", "North, Central America & Caribbean", -6, 18),
    ("Honduras", "North, Central America & Caribbean", -6, 10.5),
    ("El Salvador", "North, Central America & Caribbean", -6, 6.3),
    ("Nicaragua", "North, Central America & Caribbean", -6, 7),
    ("Costa Rica", "North, Central America & Caribbean", -6, 5.2),
    ("Panama", "North, Central America & Caribbean", -5, 4.5),
    ("Belize", "North, Central America & Caribbean", -6, 0.4),

    # Caribbean
    ("Cuba", "North, Central America & Caribbean", -4, 11),
    ("Haiti", "North, Central America & Caribbean", -4, 12),
    ("Dominican Republic", "North, Central America & Caribbean", -4, 11.3),
    ("Jamaica", "North, Central America & Caribbean", -5, 2.8),
    ("Puerto Rico", "North, Central America & Caribbean", -4, 3.2),
    ("Trinidad and Tobago", "North, Central America & Caribbean", -4, 1.5),
    ("Bahamas", "North, Central America & Caribbean", -4, 0.4),
    ("Barbados", "North, Central America & Caribbean", -4, 0.3),
    ("Guadeloupe", "North, Central America & Caribbean", -4, 0.4),
    ("Martinique", "North, Central America & Caribbean", -4, 0.35),
    ("Curacao", "North, Central America & Caribbean", -4, 0.15),
    ("Aruba", "North, Central America & Caribbean", -4, 0.11),
    ("US Virgin Islands", "North, Central America & Caribbean", -4, 0.1),
    ("Cayman Islands", "North, Central America & Caribbean", -5, 0.07),
    ("Bermuda", "North, Central America & Caribbean", -3, 0.06),
    ("Suriname", "North, Central America & Caribbean", -3, 0.6),
    ("Guyana", "North, Central America & Caribbean", -4, 0.8),

    # =========================================================================
    # SOUTH AMERICA (CONMEBOL)
    # =========================================================================

    # Brazil split by timezone [4]:
    #   Brasilia time UTC-3 (most states — SP, RJ, MG, BA, RS, PR, SC, etc.): ~195M
    #   Amazon time UTC-4 (AM, RR, RO, MT, MS): ~18M
    #   Acre time UTC-5 (AC): ~0.9M
    #   Fernando de Noronha UTC-2: ~0.003M (negligible)
    ("Brazil UTC-3 (Brasilia/most states)", "South America", -3, 195),
    ("Brazil UTC-4 (Amazonas/MT/MS)", "South America", -4, 18),
    ("Brazil UTC-5 (Acre)", "South America", -5, 0.9),

    ("Argentina", "South America", -3, 46),
    ("Colombia", "South America", -5, 52),
    ("Peru", "South America", -5, 34),
    ("Venezuela", "South America", -4, 29),
    ("Chile", "South America", -4, 20),
    ("Ecuador", "South America", -5, 18),
    ("Bolivia", "South America", -4, 12.5),
    ("Paraguay", "South America", -4, 6.8),
    ("Uruguay", "South America", -3, 3.4),
]


def build_table(data):
    """Aggregate population by region + UTC offset."""
    # Sum timezone populations
    tz_pop = defaultdict(float)
    for _, region, offset, pop in data:
        tz_pop[(region, offset)] += pop

    # Sum regional populations
    reg_pop = defaultdict(float)
    for region, offset in tz_pop:
        reg_pop[region] += tz_pop[(region, offset)]

    rows = []
    for (region, offset), pop in sorted(tz_pop.items(), key=lambda x: (x[0][0], x[0][1])):
        offset_str = format_offset(offset)
        rows.append({
            "audience_region": region,
            "utc_offset": offset_str,
            "timezone_population": round(pop, 1),
            "regional_population": round(reg_pop[region], 1),
            "regional_viewership": REGIONAL_VIEWERSHIP[region],
        })

    return rows


def format_offset(offset):
    """Format numeric offset to string like UTC-4, UTC+5:30, etc."""
    if offset == 0:
        return "UTC+0"
    sign = "+" if offset > 0 else "-"
    abs_offset = abs(offset)
    hours = int(abs_offset)
    minutes = int((abs_offset - hours) * 60)
    if minutes:
        return f"UTC{sign}{hours}:{minutes:02d}"
    return f"UTC{sign}{hours}"


def write_csv(rows, path):
    fieldnames = ["audience_region", "utc_offset", "timezone_population",
                  "regional_population", "regional_viewership"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Written {len(rows)} rows -> {path}")


def main():
    print("Building timezone population table...")
    print(f"Countries/entries: {len(COUNTRY_DATA)}")

    rows = build_table(COUNTRY_DATA)

    # Print summary
    print(f"\nRegion summary:")
    seen = set()
    for r in rows:
        reg = r["audience_region"]
        if reg not in seen:
            offsets = [x["utc_offset"] for x in rows if x["audience_region"] == reg]
            print(f"  {reg}: {r['regional_population']}M across {len(offsets)} UTC offsets")
            seen.add(reg)

    write_csv(rows, OUTPUT_CSV)

    print(f"\nOutput: {OUTPUT_CSV}")
    print("\nSources:")
    print("  [1] UN World Population Prospects 2024 — https://population.un.org/wpp/")
    print("  [2] US Census Bureau — https://www.census.gov/data/tables/time-series/demo/popest/2020s-state-total.html")
    print("  [3] Statistics Canada — https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000901")
    print("  [4] IBGE Brazil — https://www.ibge.gov.br/estatisticas/sociais/populacao.html")
    print("  [5] BPS Indonesia — https://www.bps.go.id/")
    print("  [6] ABS Australia — https://www.abs.gov.au/statistics/people/population")
    print("  [7] INEGI Mexico — https://www.inegi.org.mx/")
    print("  [8] Rosstat Russia — https://rosstat.gov.ru/")
    print("  [9] FIFA/Nielsen Qatar 2022 Global Viewership Report")


if __name__ == "__main__":
    main()
