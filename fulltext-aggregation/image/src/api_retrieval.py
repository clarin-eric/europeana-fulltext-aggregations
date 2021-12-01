import common
import os
import requests
import json
import urllib
import logging

DO_LOG_PROGRESS = True
PROGRESS_STATUS_INTERVAL = 10
DO_SAVE_METADATA = True
DO_SAVE_FULLTEXT = True
SEARCH_RESULT_PROFILE = 'minimal'
SEARCH_API_REQUEST_ROWS = 50

logger = logging.getLogger(__name__)


def retrieve(collection_id, output_base_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    # Apply configuration
    search_api_url = common.get_mandatory_env_var('SEARCH_API_URL')
    record_api_url = common.get_mandatory_env_var('RECORD_API_URL')
    api_key = common.get_mandatory_env_var('SEARCH_API_KEY')
    iiif_api_url = common.get_mandatory_env_var('IIIF_API_URL')
    records_limit = int(common.get_optional_env_var('RECORD_RETRIEVAL_LIMIT', "1"))
    if records_limit < 0:
        records_limit = None

    if output_base_dir is None:
        output_base_dir = os.curdir

    # Retrieve identifiers for records in collection
    ids = retrieve_record_ids(api_key, search_api_url, collection_id, records_limit)

    if DO_SAVE_METADATA:
        # Retrieve full metadata records for collected identifiers
        metadata_dir = common.get_metadata_dir(output_base_dir, collection_id)
        os.makedirs(name=metadata_dir, exist_ok=True)
        retrieve_and_store_metadata_records(api_key, record_api_url, metadata_dir, ids)

    if DO_SAVE_FULLTEXT:
        # Retrieve all full-text content for collected identifiers
        fulltext_dir = common.get_fulltext_dir(output_base_dir, collection_id)
        os.makedirs(name=fulltext_dir, exist_ok=True)
        retrieve_and_store_full_text(iiif_api_url, ids, fulltext_dir)


def retrieve_record_ids(api_key, api_url, collection_id, records_limit):
    """
    Retrieves the records for all objects in the specified collection, stores the JSON representations to disk
    and produces a list of identifiers for all retrieved records
    :param api_key:
    :param api_url:
    :param collection_id:
    :param records_limit:
    :return: list of identifiers
    """
    logger.info(f"Starting retrieval of record ids from collection {collection_id} from API at {api_url}")
    if records_limit is None:
        logger.info("No record retrieval limit is set, will attempt to retrieve ALL records from the collection!")
    else:
        logger.info(f"Record retrieval limit has been set to {records_limit}, will not attempt to retrieve more.")

    cursor = "*"
    ids = []
    last_status = 0

    # Paginate (using cursor) over search results
    while cursor is not None and (records_limit is None or len(ids) < records_limit):
        collection_items_response = retrieve_search_records(
            api_url, api_key, collection_id, SEARCH_API_REQUEST_ROWS, cursor)
        if "error" in collection_items_response:
            print(f"Error: {collection_items_response['error']}")
            exit(1)
        cursor = collection_items_response.get("nextCursor")
        items = collection_items_response["items"]

        # Extract identifiers and add to list
        ids += [item["id"] for item in items]
        logger.debug(f"{len(ids)} ids collected so far (cursor: {cursor})")

        # Progress logging
        if DO_LOG_PROGRESS:
            if len(ids) - last_status > PROGRESS_STATUS_INTERVAL:
                total_count = collection_items_response.get("totalResults")
                last_status = len(ids)
                if records_limit is None:
                    logger.info(f"Identifier retrieval progress: {last_status}/{total_count} "
                                f"- {last_status / total_count:2.2%})")
                else:
                    logger.info(f"Identifier retrieval progress: "
                                f"{last_status}/{total_count} "
                                f"({last_status / min(total_count, records_limit):2.2%} "
                                f"- {last_status / total_count:2.2%} of total)")

    # Cut off any extra identifiers (due to pagination we may have exceeded the configured limit)
    if records_limit is not None and len(ids) > records_limit:
        ids = ids[0:records_limit]

    logger.info(f"Done. Collected metadata and ids for {len(ids)} records from collection {collection_id}")
    return ids


def retrieve_search_records(api_base_url, api_key, collection_id, rows, cursor):
    params = {
        'wskey': api_key,
        'rows': rows,
        'cursor': cursor,
        'query': f"europeana_collectionName:{collection_id}*",
        'profile': SEARCH_RESULT_PROFILE,
        'reusability': open,
        'media': 'true'
    }
    collection_items_url = f"{api_base_url}?{urllib.parse.urlencode(params)}"
    return get_json_from_http(collection_items_url)


def retrieve_and_store_metadata_records(api_key, api_url, target_dir, ids):
    logger.info(f"Starting retrieval of metadata records for {len(ids)} objects from API at {api_url}")

    total_count = len(ids)
    report_count = 0

    # get and save records for all ids
    for record_id in ids:
        item_content = retrieve_metadata_record(api_url, api_key, record_id)
        file_name = f"{target_dir}/{common.id_to_filename(record_id)}.json"
        # save metadata record for each object
        with open(file_name, "w") as text_file:
            text_file.write(item_content)

        # Progress logging
        if DO_LOG_PROGRESS:
            report_count += 1
            if report_count % PROGRESS_STATUS_INTERVAL == 0:
                logger.info(f"Metadata record retrieval progress: "
                            f"{report_count}/{total_count} "
                            f"({report_count / total_count:2.2%})")


def retrieve_metadata_record(api_base_url, api_key, record_id):
    params = {
        'wskey': api_key
    }
    url = f"{api_base_url}{record_id}.json?{urllib.parse.urlencode(params)}"
    return requests.get(url).text


def retrieve_and_store_full_text(api_base_url, ids, target_dir):
    logger.info(f"Starting retrieval of fulltext for {len(ids)} records from API at {api_base_url}")

    total_count = len(ids)
    report_count = 0
    for record_id in ids:
        logger.debug(f"Retrieving fulltext content for {record_id}")
        iiif_manifest_url = f"{api_base_url}/presentation{record_id}/manifest"
        logger.debug(f"Getting manifest for {record_id} from {iiif_manifest_url}")
        manifest = get_json_from_http(iiif_manifest_url)

        # collection annotation URLs for record
        annotation_urls = []
        for sequence in manifest.get("sequences", []):
            for canvas in sequence.get("canvases", []):
                for otherContent in canvas.get("otherContent", []):
                    if isinstance(otherContent, str) and otherContent.startswith(api_base_url):
                        annotation_urls += [otherContent]

        # save annotations
        if len(annotation_urls) > 0:
            logger.debug(f"Found {len(annotation_urls)} annotation URLs. Retrieving content...")
            annotations = retrieve_full_text_annotations(annotation_urls)
            if len(annotations) > 0:
                save_annotations_to_file(target_dir, {record_id: annotations})
        else:
            logger.warning(f"No full-text annotation URLs found in manifest for {record_id}")

        # progress logging
        if DO_LOG_PROGRESS:
            report_count += 1
            if report_count % PROGRESS_STATUS_INTERVAL == 0:
                logger.info(f"Fulltext record retrieval progress: "
                            f"{report_count}/{total_count} "
                            f"({report_count / total_count:2.2%})")


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
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.error(f"Error decoding response from {url}")
        return None


def save_records_to_file(target_dir, items):
    """
    Saves each item in the array to a file '{id}.json' in the target directory
    """
    for item in items:
        file_name = f"{target_dir}/{common.id_to_filename(item['id'])}.json"
        logger.debug(f"Storing metadata in {file_name}")
        with open(file_name, "w") as text_file:
            text_file.write(json.dumps(item))


def save_annotations_to_file(target_dir, annotations_dict):
    for record_id in annotations_dict:
        annotations = annotations_dict[record_id]
        file_name = f"{target_dir}/{common.id_to_filename(record_id)}.txt"
        logger.debug(f"Storing fulltext content in {file_name}")
        with open(file_name, "w") as text_file:
            for annotation in annotations:
                text_file.write(annotation)


