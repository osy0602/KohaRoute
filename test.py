"""OpenRouteService Directions quick test (Auckland, 3 points).

Setup (once):
    pip install requests folium
    Make a file named .env in the SAME folder as this script, containing one line:
        ORS_API_KEY=your-key
    (add .env to .gitignore so the key is never committed)
Run:
    Press the VS Code Run button (or: python ors_test.py)
    -> prints distance/duration, writes route_map.html next to this script
"""
import os
from pathlib import Path
import requests
import folium

HERE = Path(__file__).resolve().parent


def load_key():
    # 1) environment variable, 2) .env file next to this script
    key = os.environ.get("ORS_API_KEY", "").strip()
    env_file = HERE / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "ORS_API_KEY":
                key = value.strip().strip('"').strip("'")
    if not key:
        raise SystemExit(f"No key found. Create {env_file} with the line: ORS_API_KEY=your-key")
    return key


API_KEY = load_key()
URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

# ORS uses [longitude, latitude] order (opposite of Google Maps / folium)
points = [
    [174.7633, -36.8485],  # Auckland CBD (depot)
    [174.7762, -36.8781],  # Newmarket
    [174.7400, -36.8670],  # Mt Eden
]

resp = requests.post(
    URL,
    headers={"Authorization": API_KEY, "Content-Type": "application/json"},
    json={"coordinates": points},
    timeout=20,
)
resp.raise_for_status()
data = resp.json()

feature = data["features"][0]
summary = feature["properties"]["summary"]
line = feature["geometry"]["coordinates"]  # list of [lon, lat] along the roads

print(f"distance: {summary['distance'] / 1000:.2f} km")
print(f"duration: {summary['duration'] / 60:.1f} min")
print(f"geometry points: {len(line)}  first 3: {line[:3]}")

# folium wants [lat, lon], so flip each pair
m = folium.Map(location=[points[0][1], points[0][0]], zoom_start=13)
folium.PolyLine([[lat, lon] for lon, lat in line], weight=5).add_to(m)
for i, (lon, lat) in enumerate(points):
    folium.Marker([lat, lon], tooltip=f"stop {i}").add_to(m)
m.save(HERE / "route_map.html")
print(f"saved {HERE / 'route_map.html'} (open it in a browser)")

# Open the same stop order in Google Maps (no API key needed).
# Google recalculates the road route itself; we only pass our stop order.
# Limit: about 9 waypoints between origin and destination (fewer on some mobile browsers).
from urllib.parse import urlencode

def google_maps_url(stops):
    as_text = [f"{lat},{lon}" for lon, lat in stops]  # Google wants "lat,lon"
    params = {"api": 1, "origin": as_text[0], "destination": as_text[-1], "travelmode": "driving"}
    if len(as_text) > 2:
        params["waypoints"] = "|".join(as_text[1:-1])
    return "https://www.google.com/maps/dir/?" + urlencode(params)

gmaps = google_maps_url(points)
print("Google Maps:", gmaps)
import webbrowser
webbrowser.open(gmaps)
