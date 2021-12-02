import logging
import os
import json
import unidecode
import re
from lxml import etree

EDM_NAMESPACES = {
    'rdf':      'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'edm':      'http://www.europeana.eu/schemas/edm/',
    'dc':       'http://purl.org/dc/elements/1.1/',
    'dcterms':  'http://purl.org/dc/terms/'
}

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir, output_filename='output.json'):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    # 'index' metadata records based on properties
    logger.info("Making index for metadata")
    index = make_md_index(metadata_dir)

    logger.info(f"Writing index to file {output_filename}")
    with open(output_filename, 'w') as output_file:
        json.dump(index, output_file, indent=True)

    # TODO: generate CMDI for property combinations
    # only for records that have full-text!

    logger.info("Done")


def make_md_index(metadata_dir):
    index = {}
    files = os.listdir(metadata_dir)
    logger.info(f"Reading metadata from {len(files)} files in {metadata_dir}")
    for filename in files:
        if filename.endswith(".xml"):
            file_path = f"{metadata_dir}/{filename}"
            logger.debug(f"Processing metadata file {file_path}")
            try:
                doc = etree.parse(file_path)
                identifiers = xpath_text_values(doc, '/rdf:RDF/edm:ProvidedCHO/dc:identifier')
                if len(identifiers) == 0:
                    logger.error(f"No identifier in {file_path}")
                else:
                    identifier = identifiers[0]
                    titles = [normalize_title(title)
                              for title in xpath_text_values(doc, '/rdf:RDF/edm:ProvidedCHO/dc:title')]
                    years = [date_to_year(date)
                             for date in xpath_text_values(doc, '/rdf:RDF/edm:ProvidedCHO/dcterms:issued')]

                    add_to_index(identifier, titles, years, index)
            except etree.Error as err:
                logger.error(f"Error processing XML document: {err=}")
    return index


def add_to_index(identifier, titles, years, index):
    for title in titles:
        if title not in index:
            index[title] = {}
        for year in years:
            if year not in index[title]:
                index[title][year] = []
            index[title][year] += [identifier]


def xpath_text_values(tree, path):
    nodes = tree.xpath(path, namespaces=EDM_NAMESPACES)
    if nodes is None:
        return []
    else:
        return [node.text for node in nodes]


def date_to_year(date):
    match = re.search(r"(\d{4})-\d{2}-\d{2}", date)
    if match:
        return match.group(1)
    else:
        return None


def normalize_title(title):
    match = re.search(r"^[A-z0-9'\"()\s]*[A-z0-9'\"()]", unidecode.unidecode(title))
    if match:
        return title[match.start(0):match.end(0)]
    else:
        return None

