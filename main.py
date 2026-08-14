import requests
import time

results = []

for row in routes:
    result = get_driving_data(
        row["origin_latitude"],
        row["origin_longitude"],
        row["destination_latitude"],
        row["destination_longitude"]
    )

    results.append({
        "team_id": row["team_id"],
        "venue_id": row["venue_id"],
        "driving_distance_km": result["distance_km"],
        "driving_time_hours": result["time_hours"]
    })

    time.sleep(0.2)
    
def get_driving_data(lat1, lon1, lat2, lon2):
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        "?overview=false"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    if data["code"] != "Ok":
        return None

    route = data["routes"][0]

    return {
        "distance_km": route["distance"] / 1000,
        "time_hours": route["duration"] / 3600
    }