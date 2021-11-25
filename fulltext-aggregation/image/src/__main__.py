import os
import sys
import requests
import json
import re
import urllib
import logging

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    api_url = os.environ.get('API_URL')
    api_key = os.environ.get('API_KEY')

    output_base_dir = os.environ.get('OUTPUT_DIR')
    if output_base_dir is None:
        output_base_dir = os.curdir

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
    target_dir = f"{output_base_dir}/{collection_id}"
    os.makedirs(name=target_dir, exist_ok=True)

    ids = retrieve_and_store_records(api_key, api_url, target_dir, collection_id)

    print(ids)


def retrieve_and_store_records(api_key, api_url, target_dir, collection_id):
    """
    Retrieves the records for all objects in the specified collection, stores the JSON representations to disk
    and produces a list of identifiers for all retrieved records
    :param api_key:
    :param api_url:
    :param target_dir:
    :param collection_id:
    :return: list of identifiers
    """
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
        items = collection_items_response["items"]
        ids += [item["id"] for item in items]
        logger.debug(f"{len(ids)} ids collected so far (cursor: {cursor})")
        save_records_to_file(target_dir, items)
    logger.info(f"Done. Collected {len(ids)} ids from collection {collection_id}")
    return ids


def retrieve_records(api_url, api_key, collection_id, rows, cursor):
    params = {
        'wskey': api_key,
        'rows': rows,
        'cursor': cursor,
        'query': f"europeana_collectionName:{collection_id}*",
        'profile': 'standard'}
    collection_items_url = f"{api_url}?{urllib.parse.urlencode(params)}"
    logger.debug(f"Making API request: {collection_items_url}")
    response = requests.get(collection_items_url).text
    logger.debug(f"API response: {response}")
    return json.loads(response)


def save_records_to_file(target_dir, items):
    """
    Saves each item in the array to a file '{id}.json' in the target directory
    """
    for item in items:
        file_name = f"{target_dir}/{id_to_filename(item['id'])}.json"
        logger.debug(f"Storing metadata in {file_name}")
        with open(file_name, "w") as text_file:
            text_file.write(json.dumps(item))


def id_to_filename(id):
    return re.sub(r'\/', '_', id)


if __name__ == "__main__":
    main()
