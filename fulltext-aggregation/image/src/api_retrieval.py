import os
import sys
import requests
import json
import urllib
import logging

do_save_metadata = True

logger = logging.getLogger(__name__)


def retrieve(collection_id):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    search_api_url = get_mandatory_env_var('SEARCH_API_URL')
    search_api_key = get_mandatory_env_var('SEARCH_API_KEY')
    iiif_api_url = get_mandatory_env_var('IIIF_API_URL')
    records_limit = int(get_optional_env_var('RECORD_RETRIEVAL_LIMIT', "1"))
    if records_limit < 0:
        records_limit = None

    output_base_dir = os.environ.get('OUTPUT_DIR')
    if output_base_dir is None:
        output_base_dir = os.curdir

    metadata_dir = f"{output_base_dir}/{collection_id}/metadata"
    os.makedirs(name=metadata_dir, exist_ok=True)

    ids = retrieve_and_store_records(search_api_key, search_api_url, collection_id, metadata_dir, records_limit)

    fulltext_dir = f"{output_base_dir}/{collection_id}/fulltext"
    os.makedirs(name=fulltext_dir, exist_ok=True)

    retrieve_and_store_full_text(iiif_api_url, ids, fulltext_dir)

    # TODO: create CMDI metadata for full text collection


def retrieve_and_store_records(api_key, api_url, collection_id, target_dir, records_limit):
    """
    Retrieves the records for all objects in the specified collection, stores the JSON representations to disk
    and produces a list of identifiers for all retrieved records
    :param api_key:
    :param api_url:
    :param collection_id:
    :param target_dir:
    :param records_limit:
    :return: list of identifiers
    """
    logger.info(f"Starting retrieval of record ids from collection {collection_id} from API at {api_url}")
    if records_limit is None:
        logger.info("No record retrieval limit is set, will attempt to retrieve ALL records from the collection!")
    else:
        logger.info(f"Record retrieval limit has been set to {records_limit}, will not attempt to retrieve more.")

    rows = 50
    cursor = "*"
    ids = []
    total_count = None
    last_status = 0
    status_interval = 100
    while cursor is not None and (records_limit is None or len(ids) < records_limit):
        collection_items_response = retrieve_records(api_url, api_key, collection_id, rows, cursor)
        if "error" in collection_items_response:
            print(f"Error: {collection_items_response['error']}")
            exit(1)
        if total_count is None:
            total_count = collection_items_response.get("totalResults")
        cursor = collection_items_response.get("nextCursor")
        items = collection_items_response["items"]
        ids += [item["id"] for item in items]
        logger.debug(f"{len(ids)} ids collected so far (cursor: {cursor})")
        if do_save_metadata:
            save_records_to_file(target_dir, items)
        if len(ids) - last_status > status_interval:
            last_status = len(ids)
            logger.info(f"Record retrieval progress: {last_status}/{total_count} ({last_status / total_count:2.2%})")

    if records_limit is not None and len(ids) > records_limit:
        ids = ids[0:records_limit]

    logger.info(f"Done. Collected metadata and ids for {len(ids)} records from collection {collection_id}")
    return ids


def retrieve_records(api_base_url, api_key, collection_id, rows, cursor):
    params = {
        'wskey': api_key,
        'rows': rows,
        'cursor': cursor,
        'query': f"europeana_collectionName:{collection_id}*",
        'profile': 'standard'}
    collection_items_url = f"{api_base_url}?{urllib.parse.urlencode(params)}"
    return get_json_from_http(collection_items_url)


def retrieve_and_store_full_text(api_base_url, ids, target_dir):
    logger.info(f"Starting retrieval of fulltext for {len(ids)} records from API at {api_base_url}")
    for record_id in ids:
        logger.info(f"Retrieving fulltext content for {record_id}")
        iiif_manifest_url = f"{api_base_url}/presentation{record_id}/manifest"
        logger.debug(f"Getting manifest for {record_id} from {iiif_manifest_url}")
        manifest = get_json_from_http(iiif_manifest_url)

        annotation_urls = []
        for sequence in manifest.get("sequences", []):
            for canvas in sequence.get("canvases", []):
                for otherContent in canvas.get("otherContent", []):
                    if isinstance(otherContent, str) and otherContent.startswith(api_base_url):
                        annotation_urls += [otherContent]

        if len(annotation_urls) > 0:
            logger.debug(f"Annotation urls: {annotation_urls}")
            logger.info(f"Found {len(annotation_urls)} annotation URLs. Retrieving content...")
            annotations = retrieve_full_text_annotations(annotation_urls)
            if len(annotations) > 0:
                save_annotations_to_file(target_dir, {record_id: annotations})
        else:
            logger.warning(f"No full-text annotation URLs found in manifest for {record_id}")


def retrieve_full_text_annotations(annotation_urls):
    text_annotations = []
    for url in annotation_urls:
        logger.debug(f"Retrieving annotation resources from {url}")
        response = get_json_from_http(url)
        for resource in response.get("resources", []):
            if resource.get("dcType") == "Page":
                logger.debug(f"Page level annotation resource found: {resource}")
                resource_id = resource.get("resource", {}).get("@id")
                if resource_id is None:
                    logger.error("Resource ID not found!")
                else:
                    response = get_json_from_http(resource_id)
                    text_annotations += [response.get("value")]
    return text_annotations


def get_json_from_http(url):
    logger.debug(f"Making request: {url}")
    response = requests.get(url).text
    logger.debug(f"API response: {url}")
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


def save_annotations_to_file(target_dir, annotations_dict):
    for record_id in annotations_dict:
        annotations = annotations_dict[record_id]
        file_name = f"{target_dir}/{id_to_filename(record_id)}.txt"
        logger.debug(f"Storing fulltext content in {file_name}")
        with open(file_name, "w") as text_file:
            for annotation in annotations:
                text_file.write(annotation)


def id_to_filename(value):
    return value.replace('/', '_')


def get_mandatory_env_var(name):
    value = os.environ.get(name)
    if value is None:
        print("ERROR: SEARCH_API_URL variable not set. Using default.")
        exit(1)
    return value;


def get_optional_env_var(name, default=None):
    value = os.environ.get(name)
    if value is None:
        return default
    else:
        return value
