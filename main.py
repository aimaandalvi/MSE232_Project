import requests

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