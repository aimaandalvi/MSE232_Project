import argparse
import csv
import json
import math
import os
import tempfile
from urllib.request import urlopen


DEFAULT_CSV = "travel/mse232 project - venues.csv"
DEFAULT_TEAMS_CSV = "travel/mse232 project - teams.csv"
DEFAULT_AIRPORT_MATRIX_CSV = "travel/mse232 project - airport travel.csv"
DEFAULT_TEAM_VENUE_TRAVEL_CSV = "travel/mse232 project - team venue travel.csv"
EARTH_RADIUS_KM = 6371.0088
FLIGHT_CRUISE_SPEED_KMH = 825.0
FIXED_FLIGHT_OVERHEAD_HOURS = 0.5
DRIVING_AIRPORT_PAIRS = {
    ("SNA", "LAX"),
    ("OAK", "SJC"),
    ("PBI", "FLL"),
    ("BOS", "PVD"),
    ("NLU", "MEX"),
}

def get_driving_data(lat1, lon1, lat2, lon2):
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        "?overview=false"
    )

    with urlopen(url, timeout=30) as response:
        data = json.load(response)

    if data["code"] != "Ok":
        return None

    route = data["routes"][0]

    return {
        "distance_km": route["distance"] / 1000,
        "time_hours": route["duration"] / 3600
    }


def calculate_great_circle_distance(lat1, lon1, lat2, lon2):
    """Return the Haversine great-circle distance between two points in km."""
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    # Protect atan2 from tiny floating-point excursions outside [0, 1].
    a = max(0.0, min(1.0, a))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def estimate_flight_time(distance_km):
    """Estimate one-way flight time in decimal hours."""
    return FIXED_FLIGHT_OVERHEAD_HOURS + distance_km / FLIGHT_CRUISE_SPEED_KMH


def load_airports(teams_csv_path, venues_csv_path):
    airports = {}

    def add_airport(code, longitude, latitude):
        coordinates = (float(longitude), float(latitude))
        if code in airports and airports[code] != coordinates:
            raise ValueError(
                f"Airport {code} has conflicting coordinates: "
                f"{airports[code]} and {coordinates}"
            )
        airports[code] = coordinates

    with open(teams_csv_path, newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            add_airport(
                row["base_camp_airport_code"],
                row["base_camp_airport_longitude"],
                row["base_camp_airport_latitude"],
            )

    with open(venues_csv_path, newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            add_airport(
                row["venue_airport_code"],
                row["venue_airport_longitude"],
                row["venue_airport_latitude"],
            )

    return airports


def create_airport_travel_matrix(
    teams_csv_path,
    venues_csv_path,
    output_csv_path,
):
    airports = load_airports(teams_csv_path, venues_csv_path)
    fieldnames = [
        "origin_airport_code",
        "origin_airport_longitude",
        "origin_airport_latitude",
        "destination_airport_code",
        "destination_airport_longitude",
        "destination_airport_latitude",
        "great_circle_distance_km",
        "estimated_flight_time_hours",
    ]
    rows = []

    for origin_code in sorted(airports):
        origin_longitude, origin_latitude = airports[origin_code]
        for destination_code in sorted(airports):
            if origin_code == destination_code:
                continue

            destination_longitude, destination_latitude = airports[destination_code]
            distance_km = calculate_great_circle_distance(
                origin_latitude,
                origin_longitude,
                destination_latitude,
                destination_longitude,
            )
            flight_time_hours = estimate_flight_time(distance_km)
            rows.append(
                {
                    "origin_airport_code": origin_code,
                    "origin_airport_longitude": f"{origin_longitude:.4f}",
                    "origin_airport_latitude": f"{origin_latitude:.4f}",
                    "destination_airport_code": destination_code,
                    "destination_airport_longitude": f"{destination_longitude:.4f}",
                    "destination_airport_latitude": f"{destination_latitude:.4f}",
                    "great_circle_distance_km": f"{distance_km:.3f}",
                    "estimated_flight_time_hours": f"{flight_time_hours:.3f}",
                }
            )

    output_directory = os.path.dirname(os.path.abspath(output_csv_path))
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=output_directory,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_path, output_csv_path)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    print(
        f"Created {output_csv_path} with {len(airports)} airports and "
        f"{len(rows)} directed airport pairs.",
        flush=True,
    )


def read_csv_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def validate_confirmed_airport_assignments(teams, venues):
    confirmed_team_airports = {
        "Arizona Athletic Grounds": "PHX",
        "Houston Training Centre": "IAH",
        "Florida Atlantic University": "PBI",
    }
    teams_by_base_camp = {row["base_camp_name"]: row for row in teams}
    for base_camp_name, expected_code in confirmed_team_airports.items():
        actual_code = teams_by_base_camp[base_camp_name]["base_camp_airport_code"]
        if actual_code != expected_code:
            raise ValueError(
                f"{base_camp_name} must use {expected_code}, not {actual_code}"
            )

    venues_by_name = {row["venue_name"]: row for row in venues}
    boston_airport = venues_by_name["Boston Stadium"]["venue_airport_code"]
    if boston_airport != "PVD":
        raise ValueError(f"Boston Stadium must use PVD, not {boston_airport}")


def create_team_venue_travel_csv(
    teams_csv_path,
    venues_csv_path,
    output_csv_path,
):
    teams = read_csv_rows(teams_csv_path)
    venues = read_csv_rows(venues_csv_path)
    validate_confirmed_airport_assignments(teams, venues)
    fieldnames = [
        "team_id",
        "venue_id",
        "travel_mode",
        "transportation_method",
        "origin_longitude",
        "origin_latitude",
        "destination_longitude",
        "destination_latitude",
        "driving_distance_airport_to_basecamp_one_way_km",
        "driving_time_airport_to_basecamp_one_way_hours",
        "driving_distance_airport_to_venue_one_way_km",
        "driving_time_airport_to_venue_one_way_hours",
        "airport_to_airport_distance_kilometres",
        "airport_to_airport_time_hours",
        "total_distance_travelled",
        "total_time_travelled",
    ]
    output_rows = []

    for team in teams:
        origin_airport_code = team["base_camp_airport_code"]
        origin_longitude = float(team["base_camp_airport_longitude"])
        origin_latitude = float(team["base_camp_airport_latitude"])
        for venue in venues:
            destination_airport_code = venue["venue_airport_code"]
            destination_longitude = float(venue["venue_airport_longitude"])
            destination_latitude = float(venue["venue_airport_latitude"])
            drive_only = (
                origin_airport_code == destination_airport_code
                or (origin_airport_code, destination_airport_code)
                in DRIVING_AIRPORT_PAIRS
            )
            row = {"team_id": team["team_id"], "venue_id": venue["venue_id"]}

            if drive_only:
                route_origin_longitude = float(team["base_camp_longitude"])
                route_origin_latitude = float(team["base_camp_latitude"])
                route_destination_longitude = float(venue["venue_longitude"])
                route_destination_latitude = float(venue["venue_latitude"])
                direct_route = get_driving_data(
                    route_origin_latitude,
                    route_origin_longitude,
                    route_destination_latitude,
                    route_destination_longitude,
                )
                if direct_route is None:
                    raise RuntimeError(
                        "No direct driving route found for team "
                        f"{team['team_id']} to venue {venue['venue_id']}"
                    )
                print(
                    f"Direct car route team {team['team_id']} -> "
                    f"venue {venue['venue_id']}: "
                    f"{direct_route['distance_km']:.3f} km, "
                    f"{direct_route['time_hours']:.3f} hours",
                    flush=True,
                )
                row.update(
                    {
                        "travel_mode": "DRIVE",
                        "transportation_method": "car",
                        "origin_longitude": f"{route_origin_longitude:.4f}",
                        "origin_latitude": f"{route_origin_latitude:.4f}",
                        "destination_longitude": (
                            f"{route_destination_longitude:.4f}"
                        ),
                        "destination_latitude": f"{route_destination_latitude:.4f}",
                        "driving_distance_airport_to_basecamp_one_way_km": "",
                        "driving_time_airport_to_basecamp_one_way_hours": "",
                        "driving_distance_airport_to_venue_one_way_km": "",
                        "driving_time_airport_to_venue_one_way_hours": "",
                        "airport_to_airport_distance_kilometres": "",
                        "airport_to_airport_time_hours": "",
                        "total_distance_travelled": (
                            f"{direct_route['distance_km']:.3f}"
                        ),
                        "total_time_travelled": f"{direct_route['time_hours']:.3f}",
                    }
                )
            else:
                team_airport_route = {
                    "distance_km": float(
                        team["driving_distance_airport_to_basecamp_one_way"]
                    ),
                    "time_hours": float(
                        team["driving_time_airport_to_basecamp_one_way"]
                    ),
                }
                airport_venue_route = {
                    "distance_km": float(
                        venue["driving_distance_airport_to_venue_one_way"]
                    ),
                    "time_hours": float(
                        venue["driving_time_airport_to_venue_one_way"]
                    ),
                }
                flight_distance = calculate_great_circle_distance(
                    origin_latitude,
                    origin_longitude,
                    destination_latitude,
                    destination_longitude,
                )
                flight_time = estimate_flight_time(flight_distance)
                total_distance = (
                    team_airport_route["distance_km"]
                    + flight_distance
                    + airport_venue_route["distance_km"]
                )
                total_time = (
                    team_airport_route["time_hours"]
                    + flight_time
                    + airport_venue_route["time_hours"]
                )
                row.update(
                    {
                        "travel_mode": "FLIGHT",
                        "transportation_method": "car + plane",
                        "origin_longitude": f"{origin_longitude:.4f}",
                        "origin_latitude": f"{origin_latitude:.4f}",
                        "destination_longitude": f"{destination_longitude:.4f}",
                        "destination_latitude": f"{destination_latitude:.4f}",
                        "driving_distance_airport_to_basecamp_one_way_km": (
                            f"{team_airport_route['distance_km']:.3f}"
                        ),
                        "driving_time_airport_to_basecamp_one_way_hours": (
                            f"{team_airport_route['time_hours']:.3f}"
                        ),
                        "driving_distance_airport_to_venue_one_way_km": (
                            f"{airport_venue_route['distance_km']:.3f}"
                        ),
                        "driving_time_airport_to_venue_one_way_hours": (
                            f"{airport_venue_route['time_hours']:.3f}"
                        ),
                        "airport_to_airport_distance_kilometres": (
                            f"{flight_distance:.3f}"
                        ),
                        "airport_to_airport_time_hours": f"{flight_time:.3f}",
                        "total_distance_travelled": f"{total_distance:.3f}",
                        "total_time_travelled": f"{total_time:.3f}",
                    }
                )
            output_rows.append(row)

    output_directory = os.path.dirname(os.path.abspath(output_csv_path))
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=output_directory,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)
        os.replace(temp_path, output_csv_path)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    drive_rows = sum(row["travel_mode"] == "DRIVE" for row in output_rows)
    print(
        f"Created {output_csv_path} with {len(output_rows)} team-venue rows "
        f"({drive_rows} car, {len(output_rows) - drive_rows} car + plane).",
        flush=True,
    )


def update_route_csv(
    csv_path,
    destination_name_column,
    destination_latitude_column,
    destination_longitude_column,
    airport_latitude_column,
    airport_longitude_column,
    distance_column,
    time_column,
):
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        raise ValueError(f"{csv_path} does not have a header row")

    required_columns = {
        destination_name_column,
        destination_latitude_column,
        destination_longitude_column,
        airport_latitude_column,
        airport_longitude_column,
        distance_column,
        time_column,
    }
    missing_columns = required_columns.difference(fieldnames)
    if missing_columns:
        raise ValueError(
            "Missing required CSV columns: " + ", ".join(sorted(missing_columns))
        )

    for row_number, row in enumerate(rows, start=1):
        result = get_driving_data(
            row[airport_latitude_column],
            row[airport_longitude_column],
            row[destination_latitude_column],
            row[destination_longitude_column],
        )
        if result is None:
            raise RuntimeError(
                "No driving route found for "
                f"{row.get(destination_name_column, 'unknown destination')}"
            )

        row[distance_column] = f"{result['distance_km']:.3f}"
        row[time_column] = f"{result['time_hours']:.3f}"
        print(
            f"[{row_number}/{len(rows)}] {row[destination_name_column]}: "
            f"{result['distance_km']:.3f} km, "
            f"{result['time_hours']:.3f} hours",
            flush=True,
        )

    csv_directory = os.path.dirname(os.path.abspath(csv_path))
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=csv_directory,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_path, csv_path)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def update_venue_csv(csv_path):
    update_route_csv(
        csv_path=csv_path,
        destination_name_column="venue_name",
        destination_latitude_column="venue_latitude",
        destination_longitude_column="venue_longitude",
        airport_latitude_column="venue_airport_latitude",
        airport_longitude_column="venue_airport_longitude",
        distance_column="driving_distance_airport_to_venue_one_way",
        time_column="driving_time_airport_to_venue_one_way",
    )


def update_team_csv(csv_path):
    update_route_csv(
        csv_path=csv_path,
        destination_name_column="base_camp_name",
        destination_latitude_column="base_camp_latitude",
        destination_longitude_column="base_camp_longitude",
        airport_latitude_column="base_camp_airport_latitude",
        airport_longitude_column="base_camp_airport_longitude",
        distance_column="driving_distance_airport_to_basecamp_one_way",
        time_column="driving_time_airport_to_basecamp_one_way",
    )


def update_csv(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        fieldnames = set(csv.DictReader(csv_file).fieldnames or [])

    if {"venue_latitude", "venue_longitude"}.issubset(fieldnames):
        update_venue_csv(csv_path)
    elif {"base_camp_latitude", "base_camp_longitude"}.issubset(fieldnames):
        update_team_csv(csv_path)
    else:
        raise ValueError(
            "Could not identify the CSV as a venue or team/base-camp file"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Add airport-to-destination driving distances and times to a venue or "
            "team/base-camp CSV."
        )
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=DEFAULT_CSV,
        help=f"CSV file to update in place (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--airport-matrix",
        nargs="?",
        const=DEFAULT_AIRPORT_MATRIX_CSV,
        metavar="OUTPUT_CSV",
        help=(
            "Create the Haversine airport-to-airport travel matrix, optionally at "
            f"the given path (default output: {DEFAULT_AIRPORT_MATRIX_CSV})"
        ),
    )
    parser.add_argument(
        "--team-venue-travel",
        nargs="?",
        const=DEFAULT_TEAM_VENUE_TRAVEL_CSV,
        metavar="OUTPUT_CSV",
        help=(
            "Create the combined 48-team by 16-venue travel sheet, using OSRM "
            "only for direct base-camp-to-venue car routes"
        ),
    )
    parser.add_argument(
        "--teams-csv",
        default=DEFAULT_TEAMS_CSV,
        help=(
            "Teams input for matrix/combined output "
            f"(default: {DEFAULT_TEAMS_CSV})"
        ),
    )
    parser.add_argument(
        "--venues-csv",
        default=DEFAULT_CSV,
        help=(
            "Venues input for matrix/combined output "
            f"(default: {DEFAULT_CSV})"
        ),
    )
    args = parser.parse_args()
    if args.team_venue_travel:
        create_team_venue_travel_csv(
            teams_csv_path=args.teams_csv,
            venues_csv_path=args.venues_csv,
            output_csv_path=args.team_venue_travel,
        )
    elif args.airport_matrix:
        create_airport_travel_matrix(
            teams_csv_path=args.teams_csv,
            venues_csv_path=args.venues_csv,
            output_csv_path=args.airport_matrix,
        )
    else:
        update_csv(args.csv_path)
