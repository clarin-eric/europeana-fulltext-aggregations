import os
import sys
import requests
import json
import urllib
import logging

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

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

    ids = retrieve_ids(api_key, api_url, collection_id)

    print(ids)


def retrieve_ids(api_key, api_url, collection_id):
    logger.info(f"Starting retrieval of record ids from collection {collection_id} from API at {api_url}")
    rows = 50
    cursor = "*"
    ids = []
    while cursor is not None:
        collection_items_response = retrieve_records(api_url, api_key, collection_id, rows, cursor)
        if "error" in collection_items_response:
            print(f"Error: {collection_items_response['error']}")
            exit(1)
        cursor = collection_items_response.get("nextCursor")
        ids += [item["id"] for item in collection_items_response["items"]]
        logger.debug(f"{len(ids)} ids collected (cursor: {cursor})")
    logger.info(f"Done. Collected {len(ids)} ids from collection {collection_id}")
    return ids


def retrieve_records(api_url, api_key, collection_id, rows, cursor):
    params = {
        'wskey': api_key,
        'rows': rows,
        'cursor': cursor,
        'query': f"europeana_collectionName:{collection_id}*",
        'profile': 'minimal'}
    collection_items_url = f"{api_url}?{urllib.parse.urlencode(params)}"
    logger.debug(f"Making API request: {collection_items_url}")
    response = requests.get(collection_items_url).text
    logger.debug(f"API response: {response}")
    return json.loads(response)


if __name__ == "__main__":
    main()
