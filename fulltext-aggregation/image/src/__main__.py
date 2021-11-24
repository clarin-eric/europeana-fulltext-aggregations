import os
import sys
import requests
import json


def main():
    api_url = os.environ.get('API_URL')
    api_key = os.environ.get('API_KEY')

    if api_url is None:
        print("ERROR: API_URL variable not set. Using default.")
        exit(1)

    if api_key is None:
        print("Error: API_KEY variable not set")
        exit(1)

    if len(sys.argv) <= 1:
        print("ERROR: Provide a set identifier as the first argument")
        exit(1)

    collection_id = sys.argv[1]

    collection_items = get_collection_items(api_url, api_key, collection_id)

    # TODO: extract collection identifiers
    # TODO: repeat for all pages

    print(collection_items)


def get_collection_items(apiUrl, apiKey, collectionId):
    collection_items_url = f"{apiUrl}?wskey={apiKey}&rows=10&profile=minimal&query=europeana_collectionName:{collectionId}*"

    response = requests.get(collection_items_url).text
    return json.loads(response)


if __name__ == "__main__":
    main()
