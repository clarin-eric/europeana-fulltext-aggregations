import json
import logging
import os
import requests
import time
import re

from glom import glom, PathAccessError
from lxml import etree
from multiprocessing import Pool, Manager

from aggregation_cmdi_creation import make_cmdi_record, make_cmdi_template
from aggregation_cmdi_creation import make_collection_record, make_collection_record_template
from common import log_progress
from common import get_json_from_http
from common import xpath, xpath_text_values
from common import normalize_issue_title, normalize_identifier, date_to_year, filename_safe
from common import get_optional_env_var, get_mandatory_env_var

from common import ALL_NAMESPACES
from env import THREAD_POOL_SIZE, IIIF_API_URL, RECORD_API_URL, RECORD_API_KEY

logger = logging.getLogger(__name__)

EDM_ID_PATTERN = re.compile(r'^[A-z]+://data.europeana.eu/item/([^/]+/[^/]+)$')


def aggregate(collection_id, metadata_dir, output_dir):
    start_time = time.time()

    logging.basicConfig()
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

    with Manager() as manager:
        part_of_title_map = manager.dict()
        map_lock = manager.Lock()
        with requests.Session() as session:
            indexer = FileProcessor(md_index, metadata_dir, session, total, part_of_title_map, map_lock)
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

    def __init__(self, md_index, metadata_dir, session, total, part_of_title_map, map_lock):
        self.md_index = md_index
        self.metadata_dir = metadata_dir
        self.session = session
        self.total = total
        self.count = 0
        self.last_log = 0

        self.part_of_title_map = part_of_title_map
        self.map_lock = map_lock

    def process(self, filename):
        if filename.endswith(".xml"):
            file_path = f"{self.metadata_dir}/{filename}"
            logging.debug(f"Processing metadata file {file_path}")
            return self.process_file(file_path, filename)

        self.count += 1
        self.last_log = log_progress(None, self.total, self.count, self.last_log,
                                     category="Reading metadata files",
                                     interval=1)

    def process_file(self, file_path, filename):
        try:
            doc = etree.parse(file_path)
            identifiers = xpath_text_values(doc, '/rdf:RDF/ore:Proxy/dc:identifier')
            if len(identifiers) == 0:
                logger.error(f"No identifier in {file_path}")
            else:
                identifier = normalize_identifier(identifiers[0])
                titles = self.get_titles(doc)
                years = [date_to_year(date)
                         for date in xpath_text_values(doc, '/rdf:RDF/ore:Proxy/dcterms:issued')]

                # ideally we can get the IIIF manifest URL
                iiif_manifest_urls = xpath(doc, '/rdf:RDF/edm:WebResource/dcterms:isReferencedBy/@rdf:resource')
                if iiif_manifest_urls is not None:
                    manifest_urls = [ref for ref in set(iiif_manifest_urls) if ref.startswith(IIIF_API_URL)]

                # if this does not work, we can construct one based on the CHO id
                if manifest_urls is None or len(manifest_urls) == 0:
                    constructed = construct_iiif_reference(doc)
                    if constructed:
                        manifest_urls = [constructed]

                return {
                    'identifier': identifier,
                    'titles': titles,
                    'years': years,
                    'filename': filename,
                    'manifest_urls': manifest_urls
                }

        except etree.Error as err:
            logger.error(f"Error processing XML document: {err=}")

    def get_titles(self, doc):
        # look up (newspaper) collection title (or use previously looked up)
        part_of_refs = xpath(doc, '/rdf:RDF/ore:Proxy/dcterms:isPartOf/@rdf:resource')
        titles = [self.look_up_title(ref) for ref in part_of_refs if ref is not None]
        titles = [title for title in titles if title is not None]
        if titles and len(titles) > 0:
            return titles

        # use normalized issue title(s)
        return [normalize_issue_title(title)
                for title
                in xpath_text_values(doc, '/rdf:RDF/edm:ProvidedCHO/dc:title')]

    def look_up_title(self, ref):
        # mplog = log_to_stderr()
        # mplog.setLevel(logging.INFO)
        with self.map_lock:
            from_map = self.part_of_title_map.get(ref, None)
            if from_map:
                # fetch title from map (cache)
                return from_map
            else:
                # retrieve title from API
                match = EDM_ID_PATTERN.match(ref)
                if match:
                    edm_id = match.group(1)
                    url = f"{RECORD_API_URL}/{edm_id}.json?wskey={RECORD_API_KEY}"
                    # mplog.info(f"Getting collection record from {url}")
                    json_doc = get_json_from_http(url)
                    if json_doc is not None:
                        proxies = glom(json_doc, 'object.proxies', default=None, skip_exc=PathAccessError)
                        if proxies:
                            for proxy in proxies:
                                titles = glom(proxy, 'dcTitle.def', default=None, skip_exc=PathAccessError)
                                if titles and len(titles) > 0:
                                    title = titles[0]
                                    # mplog.info(f"Setting title in map: {ref} -> {title}")
                                    self.part_of_title_map[ref] = title
                                    return title


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
    collection_template = make_collection_record_template()
    total = sum([len(index[title]) for title in index])
    count = 0
    last_log = 0

    files_created = []
    for title in index:
        files_for_years = {}
        years = index[title]
        for year in years:
            # for each year there is a dict of identifier -> {file, annotation_ref[]}
            records = years[year]

            if file_created := generate_cmdi_record(records, collection_id, title, year,
                                                    output_dir, metadata_dir, template):
                files_for_years[year] = file_created

            count += 1
            last_log = log_progress(logger, total, count, last_log,
                                    category="Generating CMDI records",
                                    interval=1)

        logger.info(f"{len(files_for_years)} year records generated for title '{title}'")

        if len(files_for_years) > 1:
            # Make a 'parent' record for the title that links to all years
            logger.info(f"Generating collection record for title '{title}'")
            generate_collection_record(collection_id, title, files_for_years, output_dir, collection_template)


def generate_cmdi_record(records, collection_id, title, year, output_dir, metadata_dir, template):
    file_name = f"{filename_safe(title + '_' + year)}.cmdi"
    file_path = f"{output_dir}/{file_name}"
    logger.debug(f"Generating metadata file {file_path}")
    if cmdi_file := make_cmdi_record(template, collection_id, title, year, records, metadata_dir):
        write_xml_tree_to_file(cmdi_file, file_path)
        return file_name


def generate_collection_record(collection_id, title, year_files, output_dir, template):
    file_name = f"{filename_safe(title + '_collection')}.cmdi"
    file_path = f"{output_dir}/{file_name}"
    logger.debug(f"Generating metadata file {file_path}")
    if cmdi_file := make_collection_record(template, collection_id, title, year_files):
        write_xml_tree_to_file(cmdi_file, file_path)


def write_xml_tree_to_file(cmdi_file, file_name):
    # wrap up and write to file
    etree.indent(cmdi_file, space="  ", level=0)
    etree.cleanup_namespaces(cmdi_file, top_nsmap=ALL_NAMESPACES)
    cmdi_file.write(file_name, encoding='utf-8', pretty_print=True, xml_declaration=True)


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


def construct_iiif_reference(doc):
    cho_identifier = xpath(doc, '/rdf:RDF/edm:ProvidedCHO/@rdf:about')
    if len(cho_identifier) == 1:
        # example identifier value:
        # http://data.europeana.eu/item/9200356/BibliographicResource_3000100359046
        match = re.search(r'\/([^\/]+\/[^\/]+)$', cho_identifier[0])
        if match:
            # example manifest URL:
            # https://iiif.europeana.eu/presentation/9200356/BibliographicResource_3000100359046/manifest
            return f"{IIIF_API_URL}/presentation/{match.group(1)}/manifest"
    return None


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
