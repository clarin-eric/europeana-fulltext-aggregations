import os
import sys
import requests
import json
import urllib


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

    rows = 50
    cursor = "*"
    total_results = -1
    ids = []
    while cursor is not None:
        collection_items_response = get_collection_items(api_url, api_key, collection_id, rows, cursor)
        if "error" in collection_items_response:
            print(f"Error: {collection_items_response['error']}")
            exit(1)
        cursor = collection_items_response.get("nextCursor")
        ids += [item["id"] for item in collection_items_response["items"]]
        print(f"{len(ids)} ids collected (cursor: {cursor})")


    # TODO: extract collection identifiers
    # TODO: repeat for all pages

    print(ids)


def get_collection_items(api_url, api_key, collection_id, rows, cursor):
    params = {
        'wskey': api_key,
        'rows': rows,
        'cursor': cursor,
        'query': f"europeana_collectionName:{collection_id}*",
        'profile': 'minimal'}
    collection_items_url = f"{api_url}?{urllib.parse.urlencode(params)}"
    response = requests.get(collection_items_url).text
    return json.loads(response)


if __name__ == "__main__":
    main()
