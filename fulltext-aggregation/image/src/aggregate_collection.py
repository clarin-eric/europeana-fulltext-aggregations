import json
import logging
import os
import requests
import time

from lxml import etree
from multiprocessing import Pool

from aggregation_cmdi_creation import make_cmdi_record, make_cmdi_template
from common import log_progress
from common import xpath, xpath_text_values
from common import normalize_title, normalize_identifier, date_to_year, filename_safe
from common import get_optional_env_var

from common import ALL_NAMESPACES

logger = logging.getLogger(__name__)

THREAD_POOL_SIZE = int(get_optional_env_var('FILE_PROCESSING_THREAD_POOL_SIZE', '10'))
IIIF_API_URL = get_optional_env_var('IIIF_API_URL', 'https://iiif.europeana.eu')


def aggregate(collection_id, metadata_dir, output_dir):
    start_time = time.time()

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.INFO)
    logger.info(f"Start time: {time.strftime('%c', time.localtime(start_time))}")

    os.makedirs(output_dir, exist_ok=True)

    # 'index' metadata records based on properties
    logger.info("Making index for metadata")
    index = make_md_index(metadata_dir)

    # save index to file in output directory
    logger.info(f"Writing index to file")
    save_index(index, f"{output_dir}/index.json")

    # generate CMDI for the indexed property combinations
    logger.info(f"Creating CMDI record for items in index in {output_dir}")
    generate_cmdi_records(collection_id, index, metadata_dir, output_dir)

    end_time = time.time()

    logger.info(f"Aggregation of {collection_id} completed in {end_time - start_time:,.2f} seconds")
    return index


def make_md_index(metadata_dir):
    md_index = {}
    files = os.listdir(metadata_dir)
    logger.info(f"Reading metadata from {len(files)} files in {metadata_dir}")
    total = len(files)

    with requests.Session() as session:
        indexer = FileProcessor(md_index, metadata_dir, session, total)
        with Pool(int(THREAD_POOL_SIZE)) as p:
            data = p.map(indexer.process, files)

        for item in data:
            # non-matching files yield no response
            if item is not None:
                add_to_index(md_index,
                             identifier=item['identifier'],
                             titles=item['titles'],
                             years=item['years'],
                             filename=item['filename'],
                             manifest_urls=item['manifest_urls'])

    return md_index


class FileProcessor:

    def __init__(self, md_index, metadata_dir, session, total):
        self.md_index = md_index
        self.metadata_dir = metadata_dir
        self.session = session
        self.total = total
        self.count = 0
        self.last_log = 0

    def process(self, filename):
        if filename.endswith(".xml"):
            file_path = f"{self.metadata_dir}/{filename}"
            logging.debug(f"Processing metadata file {file_path}")
            return process_file(file_path, filename)

        self.count += 1
        self.last_log = log_progress(None, self.total, self.count, self.last_log,
                                     category="Reading metadata files",
                                     interval=1)


def process_file(file_path, filename):
    try:
        doc = etree.parse(file_path)
        identifiers = xpath_text_values(doc, '/rdf:RDF/ore:Proxy/dc:identifier')
        if len(identifiers) == 0:
            logger.error(f"No identifier in {file_path}")
        else:
            identifier = normalize_identifier(identifiers[0])
            titles = [normalize_title(title)
                      for title in xpath_text_values(doc, '/rdf:RDF/ore:Proxy/dc:title')]
            years = [date_to_year(date)
                     for date in xpath_text_values(doc, '/rdf:RDF/ore:Proxy/dcterms:issued')]

            iiif_referencees = xpath(doc, '/rdf:RDF/edm:WebResource/dcterms:isReferencedBy/@rdf:resource')
            manifest_urls = list(set(iiif_referencees))

            return {
                'identifier': identifier,
                'titles': titles,
                'years': years,
                'filename': filename,
                'manifest_urls': manifest_urls
            }

    except etree.Error as err:
        logger.error(f"Error processing XML document: {err=}")


def add_to_index(index, identifier, titles, years, filename, manifest_urls):
    for title in titles:
        if title not in index:
            index[title] = {}
        for year in years:
            if year not in index[title]:
                index[title][year] = {}
            index[title][year][identifier] = {
                'file': filename,
                'manifest_urls': manifest_urls
            }


def save_index(index, index_filename):
    with open(index_filename, 'w') as output_file:
        json.dump(index, output_file, indent=True)


def generate_cmdi_records(collection_id, index, metadata_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    template = make_cmdi_template()
    total = sum([len(index[title]) for title in index])
    count = 0
    last_log = 0
    for title in index:
        years = index[title]
        for year in years:
            # for each year there is a dict of identifier -> {file, annotation_ref[]}
            records = years[year]
            file_name = f"{output_dir}/{filename_safe(title + '_' + year)}.cmdi"

            logger.debug(f"Generating metadata file {file_name}")
            cmdi_file = make_cmdi_record(template, collection_id, title, year, records, metadata_dir)

            # wrap up and write to file
            etree.indent(cmdi_file, space="  ", level=0)
            etree.cleanup_namespaces(cmdi_file, top_nsmap=ALL_NAMESPACES)
            cmdi_file.write(file_name, encoding='utf-8', pretty_print=True, xml_declaration=True)

            count += 1
            last_log = log_progress(logger, total, count, last_log,
                                    category="Generating CMDI records",
                                    interval=1)


def collect_fulltext_ids(fulltext_dir):
    ids = {}
    files = os.listdir(fulltext_dir)
    total = len(files)
    count = 0
    last_log = 0
    for filename in files:
        if filename.endswith(".xml"):
            file_path = f"{fulltext_dir}/{filename}"
            identifier = extract_fulltext_record_id(file_path)
            if identifier is not None:
                logger.debug(f"Extracted identifier {identifier}")
                ids[normalize_identifier(identifier)] = filename
        count += 1
        last_log = log_progress(logger, total, count, last_log,
                                category="Collecting identifiers from fulltext",
                                interval=5)

    return ids


def extract_fulltext_record_id(file_path):
    target_element = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'
    context = etree.iterparse(file_path,
                              events=('end',), tag=target_element,
                              huge_tree=True)
    for event, element in context:
        if element.tag == target_element:
            xml_base = element.get("{http://www.w3.org/XML/1998/namespace}base")
            if xml_base is None:
                logger.error(f"Expecting identifier in @xml:base of root, but not found in {file_path}")
                return None
            else:
                return xml_base
        element.clear()
    return None


# --------- Helpers ---------


def test_run():
    collection_id = '9200396'
    # result = aggregate(collection_id,
    #                    metadata_dir=f"./test-input/{collection_id}",
    #                    output_dir=f"./test-output/{collection_id}")

    with open(f"./test-input/{collection_id}/index.json", 'r') as index_file:
        index = json.load(index_file)

    generate_cmdi_records(collection_id, index,
                          metadata_dir=f"./test-input/{collection_id}",
                          output_dir=f"./test-output/{collection_id}")
    # pprint.pprint(result)


if __name__ == "__main__":
    test_run()
