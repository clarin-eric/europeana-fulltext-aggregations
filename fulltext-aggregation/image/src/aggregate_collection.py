import json
import logging
import os
import pprint

from lxml import etree

from aggregation_cmdi_creation import make_cmdi_record
from common import log_progress
from common import xpath_text_values
from common import normalize_title, normalize_identifier, date_to_year, filename_safe
from common import ALL_NAMESPACES

logger = logging.getLogger(__name__)


def aggregate(collection_id, metadata_dir, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    # 'index' metadata records based on properties
    logger.info("Making index for metadata")
    index = make_md_index(metadata_dir)


    # # save index to file in output directory
    # logger.info(f"Writing index to file")
    # save_index(index, f"{output_dir}/index.json")
    # # collect identifiers for fulltext records
    # logger.info("Collecting fulltext identifiers")
    # fulltext_id_file_map = collect_fulltext_ids(fulltext_dir)
    # # generate CMDI for the indexed property combinations
    # logger.info(f"Creating CMDI record for items in index in {output_dir}")
    # generate_cmdi_records(collection_id, index, fulltext_id_file_map, metadata_dir, output_dir, None)

    logger.info("Done")
    return index


def make_md_index(metadata_dir):
    md_index = {}
    files = os.listdir(metadata_dir)
    logger.info(f"Reading metadata from {len(files)} files in {metadata_dir}")
    total = len(files)
    count = 0
    last_log = 0
    for filename in files:
        if filename.endswith(".xml"):
            file_path = f"{metadata_dir}/{filename}"
            logger.debug(f"Processing metadata file {file_path}")
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

                    #TODO: IIIF reference

                    add_to_index(md_index, identifier, titles, years, filename)
            except etree.Error as err:
                logger.error(f"Error processing XML document: {err=}")

            count += 1
            last_log = log_progress(logger, total, count, last_log,
                                    category="Reading metadata files",
                                    interval_pct=10)
    return md_index


def add_to_index(index, identifier, titles, years, filename):
    for title in titles:
        if title not in index:
            index[title] = {}
        for year in years:
            if year not in index[title]:
                index[title][year] = {}
            index[title][year][identifier] = filename


def save_index(index, index_filename):
    with open(index_filename, 'w') as output_file:
        json.dump(index, output_file, indent=True)


def generate_cmdi_records(collection_id, index, fulltext_dict, metadata_dir, output_dir, full_text_base_url):
    os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.dirname(os.path.realpath(__file__))
    template = etree.parse(f"{script_path}/fulltextresource-template.xml")
    total = sum([len(index[title]) for title in index])
    count = 0
    last_log = 0
    for title in index:
        years = index[title]
        for year in years:
            # for each year there is a dict of identifier -> file
            title_year_ids = years[year]
            # filter on availability of fulltext
            ids = dict(filter(lambda i: i[0] in fulltext_dict, title_year_ids.items()))

            if len(ids) == 0:
                logger.warning(f"No full text records available for '{title}'/{year} - skipping CMDI creation")
            else:
                logger.debug(f"Found {len(ids)} fulltext records out of "
                             f"{len(title_year_ids)} identifiers for '{title}'/{year} ")
                file_name = f"{output_dir}/{filename_safe(title + '_' + year)}.cmdi"
                logger.debug(f"Generating metadata file {file_name}")
                cmdi_file = make_cmdi_record(template, collection_id, title, year, ids, fulltext_dict, metadata_dir,
                                             full_text_base_url)
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
    result = aggregate('9200396',
              metadata_dir='/Users/twagoo/Documents/Projects/Europeana/fulltext/dumps/edm-dataset/9200396',
              output_dir='./output')
    pprint.pprint(result)


if __name__ == "__main__":
    test_run()
