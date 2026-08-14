import json
import csv
from datetime import datetime, timedelta, timezone
import re

INPUT_FILE = "worldcup.json"
MATCH_OUTPUT = "worldcup_group_schedule.csv"
GROUP_OUTPUT = "worldcup_groups.csv"


def parse_time(date_string, time_string):
    """
    Converts:
        date = "2026-06-11"
        time = "13:00 UTC-6"

    Into:
        local_time = "13:00"
        utc_offset = -6
        kickoff_local = "2026-06-11 13:00"
        kickoff_utc = "2026-06-11 19:00"
    """

    match = re.fullmatch(
        r"(\d{1,2}):(\d{2})\s+UTC([+-]\d{1,2})",
        time_string.strip()
    )

    if not match:
        return time_string, "", f"{date_string} {time_string}", ""

    hour = int(match.group(1))
    minute = int(match.group(2))
    utc_offset = int(match.group(3))

    local_datetime = datetime.strptime(
        f"{date_string} {hour:02d}:{minute:02d}",
        "%Y-%m-%d %H:%M"
    )

    offset_timezone = timezone(timedelta(hours=utc_offset))
    local_with_timezone = local_datetime.replace(tzinfo=offset_timezone)
    utc_datetime = local_with_timezone.astimezone(timezone.utc)

    return (
        f"{hour:02d}:{minute:02d}",
        utc_offset,
        local_datetime.strftime("%Y-%m-%d %H:%M"),
        utc_datetime.strftime("%Y-%m-%d %H:%M")
    )


# Read JSON
with open(INPUT_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

matches = []

for position, match in enumerate(data["matches"], start=1):

    # Only keep group-stage matches
    if not match.get("group"):
        continue

    local_time, utc_offset, kickoff_local, kickoff_utc = parse_time(
        match["date"],
        match["time"]
    )

    group_letter = match["group"].replace("Group ", "").strip()

    row = {
        "match_id": position,
        "matchday": match.get("round", ""),
        "group": group_letter,
        "team_1": match.get("team1", ""),
        "team_2": match.get("team2", ""),
        "date": match.get("date", ""),
        "local_time": local_time,
        "utc_offset_hours": utc_offset,
        "kickoff_local": kickoff_local,
        "kickoff_utc": kickoff_utc,
        "location": match.get("ground", "")
    }

    matches.append(row)


# Sort matches chronologically
matches.sort(
    key=lambda row: (
        row["kickoff_utc"],
        row["group"],
        row["team_1"]
    )
)

# Give matches chronological IDs from 1 to 72
for match_id, row in enumerate(matches, start=1):
    row["match_id"] = match_id


# Write match schedule
match_columns = [
    "match_id",
    "matchday",
    "group",
    "team_1",
    "team_2",
    "date",
    "local_time",
    "utc_offset_hours",
    "kickoff_local",
    "kickoff_utc",
    "location"
]

with open(
    MATCH_OUTPUT,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.DictWriter(file, fieldnames=match_columns)
    writer.writeheader()
    writer.writerows(matches)


# Extract each team's group
groups = {}

for match in matches:
    group = match["group"]

    if group not in groups:
        groups[group] = set()

    groups[group].add(match["team_1"])
    groups[group].add(match["team_2"])


# Write group membership file
with open(
    GROUP_OUTPUT,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:
    writer = csv.writer(file)

    writer.writerow([
        "group",
        "group_position",
        "team"
    ])

    for group in sorted(groups):
        for position, team in enumerate(sorted(groups[group]), start=1):
            writer.writerow([
                group,
                position,
                team
            ])


print(f"Created {MATCH_OUTPUT} with {len(matches)} group-stage matches.")
print(f"Created {GROUP_OUTPUT} with {sum(len(x) for x in groups.values())} teams.")