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

    rows = 100
    start = 1
    total_results = -1
    ids = []
    while total_results < 0 or start < total_results:
        collection_items_response = get_collection_items(api_url, api_key, collection_id, start, rows)
        total_results = collection_items_response["totalResults"]
        ids += [item["id"] for item in collection_items_response["items"]]
        print(f"{len(ids)} ids collected (total: {total_results})")
        start += rows

    # TODO: extract collection identifiers
    # TODO: repeat for all pages

    print(ids)


def get_collection_items(api_url, api_key, collection_id, start, rows):
    collection_items_url = f"{api_url}?wskey={api_key}&start={start}&rows={rows}&profile=minimal" \
                           + f"&query=europeana_collectionName:{collection_id}*"
    response = requests.get(collection_items_url).text
    return json.loads(response)


if __name__ == "__main__":
    main()
