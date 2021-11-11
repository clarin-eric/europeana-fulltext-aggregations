import sys
import os

apiUrl = 'https://www.europeana.eu/api/v2/search.json'
apiKey = os.environ.get('API_KEY')

if apiKey is None:
    print("Error: API_KEY variable not set")
    exit(1)

if len(sys.argv) <= 1:
    print("ERROR: Provide a set identifier as the first argument")
    exit(1)

collectionId = sys.argv[1]

collectionItemsUrl = apiUrl+'?wskey='+apiKey + '&query=europeana_collectionName:'+collectionId+'*&rows=10&fields=id'

print(collectionItemsUrl)

# TODO: retrieve collection identifiers
