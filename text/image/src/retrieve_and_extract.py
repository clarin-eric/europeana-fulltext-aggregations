import logging
import os
import time

from stream_unzip import stream_unzip
from io import BytesIO
from lxml import etree


logger = logging.getLogger(__name__)

ZIP_BASE_PATH = '/Users/twagoo/Documents/Projects/Europeana/fulltext/dumps/edm-issue'
# TODO: get from environment variable DUMP_FTP_BASE_URL
ZIP_BASE_FTP_URL = 'ftp://download.europeana.eu/newspapers/fulltext/edm_issue'


xml_parser = etree.XMLParser(resolve_entities=False, huge_tree=True, remove_pis=True)

EDM_NAMESPACES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'ore': 'http://www.openarchives.org/ore/terms/',
    'edm': 'http://www.europeana.eu/schemas/edm/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
}


def main(collection_id, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    start_time = time.perf_counter()
    logger.info(f'Retrieving and extracting fulltext from dump for collection {collection_id}')
    chunks_generator = zipped_chunks_local(collection_id)
    # chunks_generator = zipped_chunks_ftp(collection_id)
    for file_name_b, file_size, unzipped_chunks in stream_unzip(chunks_generator):
        file_name = file_name_b.decode()
        logger.info(f'Reading file from zip: {file_name}')
        xml = read_file_from_zip(file_name, unzipped_chunks)
        logger.debug('Extracting text')
        text = extract_text(BytesIO(xml))
        logger.debug('Writing text to file')
        write_to_file(text, output_dir, file_name)

    time_elapsed = time.perf_counter() - start_time
    logger.info(f'Completed in {time_elapsed/60:0.0f}m{(time_elapsed%60):02.0f}s')


def read_file_from_zip(file_name, chunks):
    content = bytearray()
    for chunk in chunks:
        content += chunk
        logger.debug(f'Getting chunk for {file_name}')
    xml = bytes(content)
    return xml


def extract_text(source):
    tree = etree.parse(source, xml_parser)
    node = tree.xpath('/rdf:RDF/edm:FullTextResource/rdf:value', namespaces=EDM_NAMESPACES)
    if len(node) > 0:
        return node[0].text


def write_to_file(text, output_dir, file_name):
    file_name_base = os.path.splitext(file_name)[0]
    output_file = f'{output_dir}/{file_name_base}.txt'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        logger.info(f'Writing text to {os.path.realpath(output_file)}')
        f.write(text)


def zipped_chunks_local(collection_id):
    path = f'{ZIP_BASE_PATH}/{collection_id}.zip'
    logger.info(f'Opening {path}')
    with open(path, mode='rb', buffering=65536) as f:
        while True:
            data = f.read(65536)
            if data:
                yield data
            else:
                break


def zipped_chunks_ftp(collection_id):
    url = f'{ZIP_BASE_FTP_URL}/{collection_id}.zip'
    logger.info(f'Opening {url}')
    # TODO: implement
    # url = f'{ZIP_BASE_URL}/{collection_id}.zip'
    # # Iterable that yields the bytes of a zip file
    # with httpx.stream('GET', url) as r:
    #     yield from r.iter_bytes(chunk_size=65536)


