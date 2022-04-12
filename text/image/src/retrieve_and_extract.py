import logging
import os
import time
import threading

from stream_unzip import stream_unzip
from io import BytesIO
from lxml import etree
from ftplib import FTP
from urllib.parse import urlparse
from queue import SimpleQueue

logger = logging.getLogger(__name__)

BLOCK_SIZE = 65536
ZIP_BASE_PATH = os.environ.get('DUMP_BASE_PATH')
ZIP_BASE_FTP_URL = os.environ.get('DUMP_FTP_BASE_URL')

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
    if os.environ.get('DEBUG', default='false').lower() == 'true':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    start_time = time.perf_counter()
    logger.info(f'Retrieving and extracting fulltext from dump for collection {collection_id}')

    chunks_generator = create_dump_chunk_generator(collection_id)

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


def create_dump_chunk_generator(collection_id):
    if ZIP_BASE_FTP_URL:
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


def zipped_chunks_ftp(collection_id):
    file = f'{collection_id}.zip'
    logger.info(f'Opening {ZIP_BASE_FTP_URL}/{file}')

    parsed_url = urlparse(ZIP_BASE_FTP_URL)
    if parsed_url.scheme != 'ftp':
        logger.warning(f'Configured base URL is "{parsed_url.scheme}", expecting "ftp"')

    ftp = FTP(parsed_url.hostname)
    ftp.login()
    ftp.cwd(parsed_url.path)

    queue = SimpleQueue()

    def ftp_thread_target():
        ftp.retrbinary(f'RETR {file}', callback=queue.put, blocksize=BLOCK_SIZE)
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
    with open(path, mode='rb', buffering=2*BLOCK_SIZE) as f:
        while True:
            data = f.read(BLOCK_SIZE)
            if data:
                yield data
            else:
                break
