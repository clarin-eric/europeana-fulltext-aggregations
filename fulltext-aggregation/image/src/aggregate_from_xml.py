import common
import logging
import os
import json
import copy
import unidecode
import re
from lxml import etree

CMDP_NS = 'http://www.clarin.eu/cmd/1/profiles/clarin.eu:cr1:p_1633000337997'

EDM_NAMESPACES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'edm': 'http://www.europeana.eu/schemas/edm/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
}

CMD_NAMESPACES = {
    'cmd': 'http://www.clarin.eu/cmd/1',
    'cmdp': CMDP_NS
}

ALL_NAMESPACES = {**EDM_NAMESPACES, **CMD_NAMESPACES}

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    # collect identifiers for fulltext records
    logger.info("Collecting fulltext identifiers")
    fulltext_ids = collect_fulltext_ids(fulltext_dir)
    # 'index' metadata records based on properties
    logger.info("Making index for metadata")
    index = make_md_index(metadata_dir)
    # save index to file in output directory
    logger.info(f"Writing index to file")
    save_index(index, f"{output_dir}/index.json")
    # generate CMDI for the indexed property combinations
    logger.info(f"Creating CMDI record for items in index in {output_dir}")
    generate_cmdi_records(index, fulltext_ids, fulltext_dir, output_dir)

    logger.info("Done")


def make_md_index(metadata_dir):
    md_index = {}
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

                    add_to_index(identifier, titles, years, md_index)
            except etree.Error as err:
                logger.error(f"Error processing XML document: {err=}")
    return md_index


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


def generate_cmdi_records(index, fulltext_ids, fulltext_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.dirname(os.path.realpath(__file__))
    template = etree.parse(f"{script_path}/fulltextresource-template.xml")
    for title in index:
        years = index[title]
        for year in years:
            # for each year there is a list of identifiers
            title_year_ids = years[year]
            # filter on availability of fulltext
            ids = [identifier
                   for identifier in title_year_ids
                   if identifier in fulltext_ids]
            if len(ids) == 0:
                logger.warning(f"No full text records available for {title}/{year} - skipping CMDI creation")
            else:
                logger.debug(f"Found {len(ids)} fulltext records out of "
                             f"{len(title_year_ids)} identifiers for '{title}'/{year} ")
                file_name = f"{output_dir}/{filename_safe(title + '_' + year)}.cmdi"
                logger.debug(f"Generating metadata file {file_name}")
                cmdi_file = make_cmdi_record(template, title, year, ids)
                cmdi_file.write(file_name)


def collect_fulltext_ids(fulltext_dir):
    ids = []
    files = os.listdir(fulltext_dir)
    count = 0
    length = len(files)
    for filename in files:
        if filename.endswith(".xml"):
            count += 1
            file_path = f"{fulltext_dir}/{filename}"
            logger.debug(f"Getting identifier from {file_path} ({count}/{length})")
            try:
                doc = etree.parse(file_path)
                root = doc.getroot()
                xml_base = root.get("{http://www.w3.org/XML/1998/namespace}base")
                if xml_base is None:
                    logger.error(f"Expecting identifier in @xml:base of root, but not found in {file_path}")
                else:
                    ids += [xml_base]
            except etree.Error as err:
                logger.error(f"Error processing XML document: {err=}")
    return ids


def make_cmdi_record(template, title, year, ids):
    cmdi_file = copy.deepcopy(template)

    # TODO: resource proxies

    components_root = xpath(cmdi_file, '/cmd:CMD/cmd:Components/cmdp:TextResource')
    if len(components_root) != 1:
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


def filter_fulltext_ids(ids, fulltext_dir):
    available_files = os.listdir(fulltext_dir)
    return list(filter(lambda identifier: id_to_fulltext_file(identifier) in available_files, ids))


def id_to_fulltext_file(identifier):
    return f"{common.id_to_filename(identifier)}.xml"


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


if __name__ == "__main__":
    index = {
        "La clef du cabinet des princes de l'Europe": {
            "1716": [
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435146",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435156",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435157",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435147",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435155",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435154",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435158",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435148",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435150",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435149",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435152",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118435153"
            ]
        },
        "Journal historique et litt\u00e9raire": {
            "1790": [
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436032",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436022",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436014",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436015",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436023",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436033",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436028"
            ],
            "1779": [
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436295",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436285",
                "http://data.theeuropeanlibrary.org/BibliographicResource/3000118436300"
            ]
        }
    }
    fulltext_ids = [
        'http://data.theeuropeanlibrary.org/BibliographicResource/3000118436032',
        'http://data.theeuropeanlibrary.org/BibliographicResource/3000118435146'
    ]
    generate_cmdi_records(index, fulltext_ids, './output/9200396/fulltext', './test-output')
