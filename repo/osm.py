import geopy
import requests
import json

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


# Define the API endpoint URL
overpass_url = "http://overpass-api.de/api/interpreter"

# Define the query to retrieve all amenities within a 1km radius of a specific location
query_template = """
    [out:json];
    (
      node["amenity"](around:<RADIUS>,<LATITUDE>,<LONGITUDE>);
      way["amenity"](around:<RADIUS>,<LATITUDE>,<LONGITUDE>);
      relation["amenity"](around:<RADIUS>,<LATITUDE>,<LONGITUDE>);
    );
    out center;
"""


geolocator = Nominatim(user_agent="stroll")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)


async def get_geocode(addr) -> geopy.Location:
    return geocode(addr)


async def get_data(lat, lon, radius):
    query = query_template.replace("<LATITUDE>", str(lat)).replace("<LONGITUDE>", str(lon)).replace("<RADIUS>", str(radius))
    response = requests.post(overpass_url, data=query)
    return json.loads(response.text)


