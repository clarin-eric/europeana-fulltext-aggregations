import logging
from stream_unzip import stream_unzip

logger = logging.getLogger(__name__)

ZIP_BASE_PATH = '/Users/twagoo/Documents/Projects/Europeana/fulltext/dumps/edm-issue'
ZIP_BASE_FTP_URL = 'ftp://download.europeana.eu/newspapers/fulltext/edm_issue'


def main(collection_id, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    chunks_generator = zipped_chunks_local(collection_id)
    # chunks_generator = zipped_chunks_ftp(collection_id)
    for file_name, file_size, unzipped_chunks in stream_unzip(chunks_generator):
        content = bytearray()
        for chunk in unzipped_chunks:
            content += chunk
            logger.debug(f'Getting chunk for {file_name}')
        logger.info(f'Read file from zip: {file_name} ({len(content)} bytes)')
        xml = bytes(content)
        logger.debug(f'Content: {xml}')
        break


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


