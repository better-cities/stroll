import openrouteservice
from openrouteservice.directions import directions

client = openrouteservice.Client(key='5b3ce3597851110001cf6248bc7f7696f4cb4c488187d0f8873a1a6b')


async def get_route(coords, profile):
    return directions(client, coords, profile=profile)


