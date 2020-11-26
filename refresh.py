#!/usr/bin/python
"""
With this module we get the POIs with the tags vegan = * and
vegetarian = * from OpenStreetMap and fill them in a file.
"""

import os         # for handling files
import time       # for sleep
import json       # read and write json
import sys        # to check the python version
import datetime   # for the timestamp
import html
import urllib3    # for the HTTP GET request

assert sys.version_info >= (3, 0)

# constants for the overpass request

## server list (from: https://wiki.openstreetmap.org/wiki/Overpass_API)
SERVERS = [
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "http://api.openstreetmap.fr/api/interpreter",
    "http://dev.overpass-api.de/api_drolbr/interpreter",
    "http://overpass-api.de/api/interpreter",
    "http://overpass.openstreetmap.fr/api/interpreter"
]
HTTP = urllib3.PoolManager()

## constants for the output files
TIMESTAMP = datetime.datetime.now()                           # the actual date and time
SCRIPTDIR = os.path.dirname(os.path.abspath(__file__))        # get the path of the directory of this script
VEGGIEMAP_TEMPFILE = SCRIPTDIR + "/js/veggiemap-data-temp.js" # the temp file to store the data from the overpass request
VEGGIEMAP_FILE = SCRIPTDIR + "/js/veggiemap-data.js"          # the data file which will be used for the map
VEGGIEMAP_OLDFILE = SCRIPTDIR + "/js/veggiemap-data_old.js"   # previous version of the data file (helpful to examine changes)

# icon mapping
# (the first element of the array is for the icon in the marker, the second is an emoji and it is used in the title)
ICON_MAPPING = {
    # Intentionally not alphabetical order
    "cuisine:pizza": ["maki_restaurant-pizza", "🍕"],
    # Alphabetical order
    "amenity:bar": ["bar", "🍸"],
    "amenity:bbq": ["bbq", "🍴"],
    "amenity:cafe": ["cafe", "☕"],
    "amenity:cinema": ["cinema", "🎦"],
    "amenity:college": ["maki_college", "🎓"],
    "amenity:fast_food": ["fast_food", "🍔"],
    "amenity:food_court": ["restaurant", "🍽️"],
    "amenity:fuel": ["fuel", "⛽"],
    "amenity:hospital": ["hospital", "🏥"],
    "amenity:ice_cream": ["ice_cream", "🍨"],
    "amenity:kindergarten": ["playground", "🧒"],
    "amenity:pharmacy": ["pharmacy", "💊"],
    "amenity:place_of_worship": ["place_of_worship", "🛐"],
    "amenity:pub": ["pub", "🍻"],
    "amenity:restaurant": ["restaurant", "🍽️"],
    "amenity:school": ["maki_school", "🏫"],
    "amenity:shelter": ["shelter", "☂️"],
    "amenity:swimming_pool": ["maki_swimming", "🏊‍♀️"],
    "amenity:theatre": ["theatre", "🎭"],
    "amenity:university": ["maki_college", "🎓"],
    "amenity:vending_machine": ["maki_shop", "🛒"],
    "historic:memorial": ["monument", "🗿"],
    "leisure:golf_course": ["golf", "🏌️"],
    "leisure:pitch": ["maki_pitch", "🏃"],
    "leisure:sports_centre": ["sports", "🤼"],
    "leisure:stadium": ["maki_stadium", "🏟️"],
    "shop:alcohol": ["alcohol", "🍷"],
    "shop:bakery": ["bakery", "🥯"],
    "shop:beauty": ["beauty", "💇"],
    "shop:bicycle": ["bicycle", "🚲"],
    "shop:books": ["library", "📚"],
    "shop:butcher": ["butcher", "🔪"],
    "shop:clothes": ["clothes", "👚"],
    "shop:confectionery": ["confectionery", "🍬"],
    "shop:convenience": ["convenience", "🏪"],
    "shop:department_store": ["department_store", "🏬"],
    "shop:doityourself": ["diy", "🛠️"],
    "shop:fishmonger": ["maki_shop", "🐟"],
    "shop:garden_centre": ["garden-centre", "🏡"],
    "shop:general": ["maki_shop", "🛒"],
    "shop:gift": ["gift", "🎁"],
    "shop:greengrocer": ["greengrocer", "🍏"],
    "shop:hairdresser": ["hairdresser", "💇"],
    "shop:kiosk": ["maki_shop", "🛒"],
    "shop:music": ["music", "🎶"],
    "shop:supermarket": ["supermarket", "🏪"],
    "shop:wine": ["alcohol", "🍷"],
    "tourism:guest_house": ["guest_house", "🏠"],
    "tourism:museum": ["museum", "🖼️"],
}


def determine_icon(tags):
    """Determine an icon for the marker."""
    icon = ["maki_star-stroked", ""]   # Use this icon if there is no matching per ICON_MAPPING.
    for kv in ICON_MAPPING:
        k, v = kv.split(":")
        t = tags.get(k)

        if not t:
            continue

        t = t.split(";")[0]

        if t == v:
            icon = ICON_MAPPING[kv]
            break
    return icon


def get_data_osm():
    """Get the data from OSM."""
    # Initialize variables
    server = 0
    result = None

    # Preparing the string for the Overpass request
    overpass_data_out = '?data=[out:json];('
    overpass_vegan_objects = 'node["diet:vegan"~"yes|only|limited"];way["diet:vegan"~"yes|only|limited"];'
    overpass_vegetarian_objects = 'node["diet:vegetarian"~"yes|only"];way["diet:vegetarian"~"yes|only"];'
    overpass_out = ');out+center;'

    # Sending a request to one server after another until one gives a valid answer or the end of the server list is reached.
    while (server < len(SERVERS)) and (result is None):
        # Get a server from the server list
        overpass_server = SERVERS[server]

        # Overpass request
        print("Send query to server: ", overpass_server)
        r = HTTP.request("GET", overpass_server + overpass_data_out + overpass_vegan_objects + overpass_vegetarian_objects + overpass_out)

        # Check the status of the request
        if r.status == 200:
            print("Received answer successfully.")
            result = json.loads(r.data.decode("utf-8"))
        elif r.status == 400:
            print("HTTP error code ", r.status, ": Bad Request")
            time.sleep(5)
        elif r.status == 429:
            print("HTTP error code ", r.status, ": Too Many Requests")
            time.sleep(60)
        elif r.status == 504:
            print("HTTP error code ", r.status, ": Gateway Timeout")
            time.sleep(600)
        else:
            print("Unknown HTTP error code: ", r.status)

        # Increase to get another server for the next pass of the loop.
        server += 1

    return result


def write_data(data):
    """Write the data in a temp file."""
    # Initialize variables to count the markers
    n_vegan_only = 0
    n_vegetarian_only = 0
    n_vegan_friendly = 0
    n_vegan_limited = 0
    n_vegetarian_friendly = 0

    with open(VEGGIEMAP_TEMPFILE, 'w') as f:
        f.write('// Created: %s\n' % (TIMESTAMP))
        f.write('function veggiemap_populate(markers) {\n')

        for e in data['elements']:
            ide = e['id']
            typ = e['type']
            tags = e.get('tags', {})

            for k in list(tags.keys()):
                # Convert characters into html entities
                # (to prevent escape any code)
                tags[k] = html.escape(tags[k])

            if typ == 'node':
                lat = e.get('lat', None)
                lon = e.get('lon', None)

            if typ == 'way':
                center_coordinates = e.get('center', None) # get the coordinates from the center of the object
                lat = center_coordinates.get('lat', None)
                lon = center_coordinates.get('lon', None)

            if not lat or not lon:
                continue

            icon = determine_icon(tags)

            if 'name' in tags:
                # The name will be shown in the popup box
                # (where the browser converts html entities).
                name = '%s %s' % (icon[1], tags['name'])

                # The title of a marker will be shown on mouse hover
                # (where the browser DON'T converts html entities (issue #25)).
                # So we reconvert the html entities into the proper characters:
                title = html.unescape(name)
                ## But double quoutes could escape code, so we have to replace them:
                title = title.replace('"', '”')
            else:
                name = '%s %s %s' % (icon[1], typ, ide)
                title = name


            # Give the object a category
            if tags.get('diet:vegan', '') == 'only':
                category = "vegan_only"
                n_vegan_only += 1
            elif (tags.get('diet:vegetarian', '') == 'only'
                  and tags.get('diet:vegan', '') == 'yes'):
                category = "vegetarian_only"
                n_vegetarian_only += 1
            elif tags.get('diet:vegan', '') == 'yes':
                category = "vegan_friendly"
                n_vegan_friendly += 1
            elif tags.get('diet:vegan', '') == 'limited':
                category = "vegan_limited"
                n_vegan_limited += 1
            else:
                category = "vegetarian_friendly"
                n_vegetarian_friendly += 1

            # Building the textbox of the Marker
            popup = '<b>%s</b> <a href=\\"https://openstreetmap.org/%s/%s\\" target=\\"_blank\\">*</a><hr/>' % (name, typ, ide)

            ## Cuisine
            if 'cuisine' in tags:
                popup += '<div class=\\"popupflex-container\\"><div>👩‍🍳</div><div>%s</div></div>' % (tags['cuisine'])

            ## Address
            placeAddress = ""
            if 'addr:street' in tags:
                placeAddress += tags.get('addr:street', '') + ' ' + tags.get('addr:housenumber', '')
            if 'addr:city' in tags:
                if placeAddress != "":
                   placeAddress += "<br/>"
                placeAddress += tags.get('addr:city', '')
            if 'addr:country' in tags:
                if placeAddress != "":
                   placeAddress += "<br/>"
                placeAddress += tags.get('addr:country', '')
            if placeAddress != "":
                popup += '<div class=\\"popupflex-container\\"><div>📍</div><div>%s</div></div>' % (placeAddress)

            ## Website
            placeWebsite = ""
            if 'contact:website' in tags:
                placeWebsite = tags['contact:website']
            elif 'website' in tags:
                placeWebsite = tags['website']
            if placeWebsite != "":
                placeWebsiteWithout = placeWebsite.replace('https://', '')
                popup += '<div class=\\"popupflex-container\\"><div>🌐</div><div><a href=\\"%s\\" target=\\"_blank\\">%s</a></div></div>' % (placeWebsite, placeWebsiteWithout)

            ## E-Mail
            placeEmail = ""
            if 'contact:email' in tags:
                placeEmail = tags['contact:email']
            elif 'email' in tags:
                placeEmail = tags['email']
            if placeEmail != "":
                popup += '<div class=\\"popupflex-container\\"><div>📧</div><div><a href=\\"mailto:%s\\" target=\\"_blank\\">%s</a><br/></div></div>' % (placeEmail, placeEmail)

            ## Phone
            placePhone = ""
            if 'contact:phone' in tags:
                placePhone = tags['contact:phone']
            elif 'phone' in tags:
                placePhone = tags['phone']
            if placePhone != "":
                popup += '<div class=\\"popupflex-container\\"><div>☎️</div><div><a href=\\"tel:%s\\" target=\\"_blank\\">%s</a><br/></div></div>' % (placePhone, placePhone)

            ## Opening hours
            if 'opening_hours' in tags:
                # Replacing line breaks with spaces (Usually there should be no line breaks,
                # but if they do appear, they break the structure of the veggiemap-data.js).
                opening_hours = tags['opening_hours'].replace('\n', '').replace('\r', '')
                # Diverting entries with break (that looks better in the popup box)
                opening_hours = opening_hours.replace("; ", "<br/>")
                popup += '<div class=\\"popupflex-container\\"><div>🕖</div><div>%s</div></div>' % (opening_hours)

            f.write('L.marker([%s,%s],{title:"%s",icon:getIcon("%s","%s")}).bindPopup("%s").addTo(%s);\n' % (lat, lon, title, icon[0], category, popup, category))

        f.write('}\n')
        f.write('let numbers = {\n n_vegan_only:%s,\n n_vegetarian_only:%s,\n n_vegan_friendly:%s,\n n_vegan_limited:%s,\n n_vegetarian_friendly:%s\n};\n' % (n_vegan_only, n_vegetarian_only, n_vegan_friendly, n_vegan_limited, n_vegetarian_friendly))


def check_data():
    """Check the temp file and replace the old VEGGIE_MAP file if it is ok."""

    if os.path.isfile(VEGGIEMAP_TEMPFILE):                  # check if the temp file exists
        if os.path.getsize(VEGGIEMAP_TEMPFILE) > 250:       # check if the temp file isn't to small (see issue #21)
            print("rename " + VEGGIEMAP_TEMPFILE + " to " + VEGGIEMAP_FILE)
            os.rename(VEGGIEMAP_FILE, VEGGIEMAP_OLDFILE)    # rename old file
            os.rename(VEGGIEMAP_TEMPFILE, VEGGIEMAP_FILE)   # rename temp file to new file
        else:
            print("temp file is to small!")
            print(os.path.getsize(VEGGIEMAP_TEMPFILE))
    else:
        print("temp file don't exists!")


def main():
    """Call the functions to get and write the osm data."""
    # Get data
    osm_data = get_data_osm()

    # Write data
    if osm_data is not None:
        write_data(osm_data)
        check_data()
    else:
        print("A problem has occurred. The old VEGGIE_MAP was not replaced!")


main()
