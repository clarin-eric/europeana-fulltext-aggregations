import logging
import os
import re
import time
import threading
import json

from stream_unzip import stream_unzip
from io import BytesIO
from lxml import etree
from ftplib import FTP
from urllib.parse import urlparse
from queue import Queue

logger = logging.getLogger(__name__)

ENV_BLOCK_SIZE = os.environ.get('BLOCK_SIZE', default='65536')
ENV_QUEUE_SIZE_LIMIT = os.environ.get('QUEUE_SIZE_LIMIT', default='1024')
ZIP_BASE_PATH = os.environ.get('DUMP_BASE_PATH')
ZIP_BASE_URL = os.environ.get('DUMP_BASE_URL')
MAP_FILE_NAME = os.environ.get('MAP_FILE_NAME', default='id_file_map.json')

xml_parser = etree.XMLParser(resolve_entities=False, huge_tree=True, remove_pis=True)

EDM_NAMESPACES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'edm': 'http://www.europeana.eu/schemas/edm/'
}

block_size = int(ENV_BLOCK_SIZE)
queue_size_limit = int(ENV_QUEUE_SIZE_LIMIT)


def main(collection_id, output_dir):
    logging.basicConfig()
    if os.environ.get('DEBUG', default='false').lower() == 'true':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    start_time = time.perf_counter()
    logger.info(f'Retrieving and extracting fulltext from dump for collection {collection_id}')

    id_file_map = {}

    chunks_generator = create_dump_chunk_generator(collection_id)
    for file_name_b, file_size, unzipped_chunks in stream_unzip(chunks_generator):
        file_name = file_name_b.decode()
        output_file = f'{os.path.splitext(file_name)[0]}.txt'
        full_output_path = f'{output_dir}/{output_file}'

        logger.info(f'Reading file from zip: {file_name}')
        xml = read_file_from_zip(file_name, unzipped_chunks)
        logger.debug('Extracting text')
        text = process_xml(BytesIO(xml), id_file_map, os.path.basename(output_file))
        logger.debug('Writing text to file')
        write_to_file(text, full_output_path)

    map_file = f'{os.path.realpath(output_dir)}/{collection_id}/{MAP_FILE_NAME}'
    logger.info(f'Writing id -> file name map to {map_file}')
    with open(map_file, 'w') as f:
        json.dump(id_file_map, f)

    time_elapsed = time.perf_counter() - start_time
    logger.info(f'Completed processing of {collection_id} in {time_elapsed/60:0.0f}m{(time_elapsed%60):02.0f}s')


def create_dump_chunk_generator(collection_id):
    if ZIP_BASE_URL:
        return zipped_chunks_ftp(collection_id)
    if ZIP_BASE_PATH:
        return zipped_chunks_local(collection_id)
    else:
        logger.error("No data to process - configure FTP or local path for dump")
        exit(1)


def read_file_from_zip(file_name, chunks):
    content = bytearray()
    for chunk in chunks:
        content += chunk
    xml = bytes(content)
    return xml


def process_xml(source, id_file_map, output_file):
    tree = etree.parse(source, xml_parser)
    # get identifier and add to map
    if id_file_map is not None:
        root_node = tree.xpath('/rdf:RDF', namespaces=EDM_NAMESPACES)
        if len(root_node) > 0:
            record_id = root_node[0].get('{http://www.w3.org/XML/1998/namespace}base')
            if record_id:
                id_file_map[normalize_identifier(record_id)] = output_file

    # get text content and return
    text_node = tree.xpath('/rdf:RDF/edm:FullTextResource/rdf:value', namespaces=EDM_NAMESPACES)
    if len(text_node) > 0:
        return text_node[0].text


def write_to_file(text, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        logger.info(f'Writing text to {os.path.realpath(output_file)}')
        f.write(text)


def zipped_chunks_ftp(collection_id):
    file = f'{collection_id}.zip'
    logger.info(f'Opening {ZIP_BASE_URL}/{file}')

    parsed_url = urlparse(ZIP_BASE_URL)
    if parsed_url.scheme != 'ftp':
        logger.warning(f'Configured base URL is "{parsed_url.scheme}", expecting "ftp"')

    ftp = FTP(parsed_url.hostname)
    ftp.login()
    ftp.cwd(parsed_url.path)

    queue = Queue(queue_size_limit)

    def ftp_thread_target():
        ftp.retrbinary(f'RETR {file}', callback=queue.put, blocksize=block_size)
        queue.put(None)

    logger.info(f'Starting retrieval from {ftp.host}')
    ftp_thread = threading.Thread(target=ftp_thread_target)
    ftp_thread.start()

    count = 0
    while True:
        chunk = queue.get()
        if chunk:
            if logger.level == logging.DEBUG:
                count += 1
                if (count % 100) == 0:
                    logger.debug(f'Chunk count: {count}. Queue size: {queue.qsize()}.')
            yield chunk
        else:
            return


def zipped_chunks_local(collection_id):
    path = f'{ZIP_BASE_PATH}/{collection_id}.zip'
    logger.info(f'Opening {path}')
    with open(path, mode='rb', buffering=2*block_size) as f:
        while True:
            data = f.read(block_size)
            if data:
                yield data
            else:
                break


def normalize_identifier(identifier):
    # ex. http://data.theeuropeanlibrary.org/BibliographicResource/3000118435146
    # ex. http://data.europeana.eu/annotation/9200396/BibliographicResource_3000118435009
    match = re.search(r"http.*[^\d](\d+)$", identifier)
    if match:
        logger.debug(f"Normalised identifier: {identifier} -> {match.group(1)}")
        return match.group(1)
    else:
        logger.warning(f"Identifier {identifier} does not match pattern, skipping normalisation!")
        return identifier