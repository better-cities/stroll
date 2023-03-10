import asyncio
import json
import csv

from fastapi import FastAPI, BackgroundTasks

from routing.routing import get_route
from repo.osm import get_data, get_geocode

app = FastAPI()

category_names = {
    "Grocery stores and markets for food shopping": ["marketplace"],
    "Pharmacies for prescription medications and health products": ["pharmacy", "hospital", "doctors", "clinic",
                                                                    "dentist"],
    "Medical clinics for routine checkups and non-emergency medical care": ["hospital", "doctors"],
    "Parks and public spaces for outdoor recreation and leisure activities": ["bench", "shelter", "drinking_water"],
    "Schools for education and child development": ["school", "college"],
    "Post offices for mail and package delivery": ["post_office", "post_box"],
    "Community centres for social events and gatherings": ["social_facility", "community_centre", "nightclub"],
    "Places of worship for religious or spiritual needs": ["place_of_worship"],
    "Restaurants and cafes for dining and socializing": ["restaurant", "fast_food", "cafe", "bar", "ice_cream", "pub"],
    "Public transportation hubs for regional and city-wide travel": ["bicycle_rental", "bus_station",
                                                                     "public_transport_stop"],
    "Fitness centres and gyms for exercise and physical activity": ["gym"],
    "Entertainment and cultural venues for art, music, and cultural events": ["theatre", "cinema", "events_venue"],
    "Childcare facilities for families with young children": ["childcare", "kindergarten"],
}
# "bench", "public_transport_stop"
all_categories = ["marketplace", "pharmacy", "hospital", "doctors", "clinic", "dentist", "shelter", "drinking_water",
                  "school", "college", "post_office", "post_box", "social_facility", "community_centre", "nightclub",
                  "place_of_worship", "restaurant", "fast_food", "cafe", "bar", "ice_cream", "pub", "bicycle_rental",
                  "car_rental", "bus_station", "gym", "theatre", "cinema", "events_venue", "childcare", "kindergarten",
                  "public_transport_stop"]


@app.get("/route")
async def route(departure: str, destination: str):
    dep, des = await get_geocode(departure), await get_geocode(destination)
    coords = ((dep.longitude, dep.latitude), (des.longitude, des.latitude))
    return await get_route(coords, "foot-walking")


@app.get("/businesses")
async def businesses(address: str, background_tasks: BackgroundTasks):
    radius = 1000
    loc = await get_geocode(address)
    data = await get_data(loc.latitude, loc.longitude, radius)
    # return await process_result(data, loc)
    background_tasks.add_task(process_result, data, loc)

    return {"message": "Processing location in the background"}


@app.get("/distance_to_transport")
async def distance_to_transport():
    tram_stops = [
        (7.196325733545356, 43.698232838994926),
        (7.203130950929075, 43.682960843196156),
        (7.201735081387961, 43.6875885406119),
        (7.199416997095028, 43.692646907792415),
    ]
    corners = [
        (7.1963753, 43.6843149),
        (7.1955384, 43.6859519),
        (7.1946765, 43.6873587),
        (7.1936402, 43.6895651),
    ]
    result = []
    for inc, c in enumerate(corners):
        for ins, s in enumerate(tram_stops):
            await asyncio.sleep(1.2)
            coords = (c, s)
            routes = await get_route(coords, "foot-walking")
            routes['routes'][0]['summary']["building_id"] = inc
            routes['routes'][0]['summary']["tram_id"] = ins
            routes['routes'][0]['summary']["building_location"] = c
            routes['routes'][0]['summary']["tram_location"] = s
            routes['routes'][0]['summary']["walkable"] = routes['routes'][0]['summary']['duration'] < 900
            routes['routes'][0]['summary']["title"] = "building " + str(inc) + " to tram " + str(ins)
            result.append(routes['routes'][0]['summary'])

    keys = result[0].keys()

    with open('result.csv', 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(result)
    return result


@app.get("/result")
async def result():
    with open('result.json', 'r') as result_data:
        return json.load(result_data)


def count_categories(categories):
    category_count = {}
    for category_name, sub_categories in category_names.items():
        count = 0
        for sub_category in sub_categories:
            count += categories.get(sub_category, 0)
        category_count[category_name] = count
    return category_count


async def in_walkable_distance(flat, flon, tlat, tlon) -> bool:
    coords = ((flon, flat), (tlon, tlat))
    routes = await get_route(coords, "foot-walking")
    duration = routes['routes'][0]['summary']['duration']
    if duration < 900:
        print("facility within 15 minutes distance")
        return True
    print("to long, expecting 15 minutes got " + str(duration / 60))
    return False


async def process_result(data, loc):
    collection = {}
    unique: dict[str:str] = {}

    for element in data["elements"]:
        t = element["tags"]["amenity"]  # type
        if t == "shelter" and element["tags"].get("shelter_type") == "public_transport":
            t = "public_transport_stop"
        if t not in all_categories:
            continue
        await asyncio.sleep(1.5)
        if element["type"] == "way":
            iwd = await in_walkable_distance(loc.latitude, loc.longitude, element["center"]["lat"],
                                             element["center"]["lon"])
            if not iwd:
                continue
        else:
            iwd = await in_walkable_distance(loc.latitude, loc.longitude, element["lat"], element["lon"])
            if not iwd:
                continue

        if t in unique:
            unique[t] += 1
        else:
            unique[t] = 1
        try:
            collection[t]["elements"].append(element)
            collection[t]["count"] = len(collection[t]["elements"])
        except KeyError:
            collection[t] = {
                "count": 1,
                "elements": [element],
            }

    with open('result.json', 'w') as outfile:
        outfile.write(json.dumps({
            "count": count_categories(unique),
            "categories": unique,
            "collection": collection,
        }))
    print("Done!")
