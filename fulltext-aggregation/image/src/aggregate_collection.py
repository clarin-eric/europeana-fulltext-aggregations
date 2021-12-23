import json
import logging
import os
import requests

from lxml import etree
from glom import glom, flatten, PathAccessError
from multiprocessing import Pool

from aggregation_cmdi_creation import make_cmdi_record
from common import log_progress
from common import xpath, xpath_text_values
from common import normalize_title, normalize_identifier, date_to_year, filename_safe
from common import get_json_from_http
from common import get_optional_env_var

from common import ALL_NAMESPACES

logger = logging.getLogger(__name__)

THREAD_POOL_SIZE = int(get_optional_env_var('API_RETRIEVAL_THREAD_POOL_SIZE', '10'))
IIIF_API_URL = get_optional_env_var('IIIF_API_URL', 'https://iiif.europeana.eu')


def aggregate(collection_id, metadata_dir, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

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

    logger.info("Done")
    return index


def make_md_index(metadata_dir):
    md_index = {}
    files = os.listdir(metadata_dir)
    logger.info(f"Reading metadata from {len(files)} files in {metadata_dir}")
    total = len(files)

    with requests.Session() as session:
        indexer = FileIndexer(md_index, metadata_dir, session, total)
        with Pool(int(THREAD_POOL_SIZE)) as p:
            p.map(indexer.index_from_file, files)

    return md_index


class FileIndexer:

    def __init__(self, md_index, metadata_dir, session, total):
        self.md_index = md_index
        self.metadata_dir = metadata_dir
        self.session = session
        self.total = total
        self.count = 0
        self.last_log = 0

    def index_from_file(self, filename):
        if filename.endswith(".xml"):
            file_path = f"{self.metadata_dir}/{filename}"
            logger.debug(f"Processing metadata file {file_path}")
            add_file_to_index(file_path, filename, self.md_index, self.session)

        self.count += 1
        self.last_log = log_progress(logger, self.total, self.count, self.last_log,
                                category="Reading metadata files",
                                interval_pct=5)


def add_file_to_index(file_path, filename, md_index, session):
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

            annotation_refs = []
            iiif_referencees = xpath(doc, '/rdf:RDF/edm:WebResource/dcterms:isReferencedBy/@rdf:resource')
            for manifest_url in list(set(iiif_referencees)):
                annotation_refs += retrieve_annotation_refs(manifest_url, session)

            add_to_index(md_index, identifier, titles, years, filename, annotation_refs)
    except etree.Error as err:
        logger.error(f"Error processing XML document: {err=}")


def retrieve_annotation_refs(iiif_manifest_url, session):
    if not iiif_manifest_url.startswith(IIIF_API_URL):
        logger.warning(f"Skipping URL, not a IIIF service URL: {iiif_manifest_url}")
        return []

    logger.debug(f"Getting manifest from {iiif_manifest_url}")
    manifest = get_json_from_http(iiif_manifest_url, session)

    if manifest is None:
        logger.warning(f"No valid response from manifest request at {iiif_manifest_url}")
    else:
        # collection annotation URLs for record
        canvases = glom(manifest, ('sequences', ['canvases']), skip_exc=PathAccessError)
        if canvases is not None:
            annotation_urls = glom(flatten(canvases), ['otherContent'], skip_exc=PathAccessError)
            if annotation_urls is not None:
                annotation_urls_flat = flatten(annotation_urls)
                logger.debug(f"{len(annotation_urls_flat)} annotation references found")
                return retrieve_fulltext_refs(annotation_urls_flat, session)

    return []


def retrieve_fulltext_refs(annotation_urls, session=None):
    refs = []
    for annotation_url in annotation_urls:
        annotations = get_json_from_http(annotation_url, session)
        if annotations is None:
            logger.error(f"No content for annotations at {annotation_url}")
        else:
            fulltext_ref = get_fulltext_ref_from_annotations(annotations)
            if fulltext_ref is None:
                logger.error(f"No full text content in annotations data at {annotation_url}")
            else:
                refs += [fulltext_ref]

    return refs


def get_fulltext_ref_from_annotations(annotations):
    resources = annotations.get('resources', None)
    if resources is None:
        logger.error(f"No resources in annotations")
    else:
        for resource in resources:
            if resource['dcType'] == 'Page':
                return glom(resource, 'resource.@id', skip_exc=PathAccessError)

    return None


def add_to_index(index, identifier, titles, years, filename, annotation_refs):
    for title in titles:
        if title not in index:
            index[title] = {}
        for year in years:
            if year not in index[title]:
                index[title][year] = {}
            index[title][year][identifier] = {
                'file': filename,
                'annotation_refs': annotation_refs
            }


def save_index(index, index_filename):
    with open(index_filename, 'w') as output_file:
        json.dump(index, output_file, indent=True)


def generate_cmdi_records(collection_id, index, metadata_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.dirname(os.path.realpath(__file__))
    template = etree.parse(f"{script_path}/fulltextresource-template.xml")
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
