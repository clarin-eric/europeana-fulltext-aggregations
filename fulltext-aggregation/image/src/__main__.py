import os
import sys
import requests
import json

apiUrl = os.environ.get('API_URL')
apiKey = os.environ.get('API_KEY')

if apiUrl is None:
    print("ERROR: API_KEY variable not set. Using default.")
    exit(1)

if apiKey is None:
    print("Error: API_KEY variable not set")
    exit(1)

if len(sys.argv) <= 1:
    print("ERROR: Provide a set identifier as the first argument")
    exit(1)

collectionId = sys.argv[1]

collectionItemsUrl = apiUrl+'?wskey=' + apiKey\
                     + '&rows=10&profile=minimal&query=europeana_collectionName:' \
                     + collectionId+'*'

response = requests.get(collectionItemsUrl).text
json = json.loads(response)

# TODO: extract collection identifiers
# TODO: repeat for all pages

print(json)


