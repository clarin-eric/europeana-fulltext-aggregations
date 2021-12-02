import logging
import os
import json
import copy
import unidecode
import re
from lxml import etree

CMDP_NS='http://www.clarin.eu/cmd/1/profiles/clarin.eu:cr1:p_1633000337997'

EDM_NAMESPACES = {
    'rdf':      'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'edm':      'http://www.europeana.eu/schemas/edm/',
    'dc':       'http://purl.org/dc/elements/1.1/',
    'dcterms':  'http://purl.org/dc/terms/',
}

CMD_NAMESPACES = {
    'cmd': 'http://www.clarin.eu/cmd/1',
    'cmdp': CMDP_NS
}

ALL_NAMESPACES = {**EDM_NAMESPACES, **CMD_NAMESPACES}

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    # 'index' metadata records based on properties
    logger.info("Making index for metadata")
    index = make_md_index(metadata_dir)
    # save index to file in output directory
    logger.info(f"Writing index to file")
    save_index(index, f"{output_dir}/index.json")
    # generate CMDI for the indexed property combinations
    logger.info(f"Creating CMDI record for items in index in {output_dir}")
    generate_cmdi_records(index, fulltext_dir, output_dir)

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


def save_index(index, index_filename):
    with open(index_filename, 'w') as output_file:
        json.dump(index, output_file, indent=True)


def generate_cmdi_records(index, fulltext_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.dirname(os.path.realpath(__file__))
    template = etree.parse(f"{script_path}/fulltextresource-template.xml")
    for title in index:
        years = index[title]
        for year in years:
            ids = years[year]
            file_name = f"{output_dir}/{filename_safe(title+'_'+year)}.cmdi"
            logger.debug(f"Generating metadata file {file_name}")
            cmdi_file = make_cmdi_record(template, title, year, ids)
            cmdi_file.write(file_name)


def make_cmdi_record(template, title, year, ids):
    cmdi_file = copy.deepcopy(template)

    # TODO: resource proxies

    components_root = xpath(cmdi_file, '/cmd:CMD/cmd:Components/cmdp:TextResource')
    if len(components_root != 1):
        logger.error("Expecting exactly one components root element")
    else:
        make_component_content(components_root, title, year)

    return cmdi_file


def make_component_content(components_root, title, year):
    # Insert title info
    title_info_node = etree.Element('{' + CMDP_NS + '}TitleInfo', nsmap=CMD_NAMESPACES)
    title_node = etree.Element('{' + CMDP_NS + '}title', nsmap=CMD_NAMESPACES)
    title_node.text = f"{title} - {year}"
    title_info_node.insert(1, title_node)
    components_root[0].insert(1, title_info_node)

    # TODO: description
    # TODO: language
    # TODO: subresources


# --------- Helpers ---------
def xpath(tree, path, namespaces=ALL_NAMESPACES):
    return tree.xpath(path, namespaces=namespaces)


def xpath_text_values(tree, path, namespaces=ALL_NAMESPACES):
    nodes = xpath(tree, path, namespaces)
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


def filename_safe(name):
    return re.sub(r"[^A-z0-9]", '_', name)
