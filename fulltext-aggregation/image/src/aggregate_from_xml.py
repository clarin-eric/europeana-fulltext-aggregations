import datetime

import common
import logging
import os
import json
import copy
import unidecode
import re
from lxml import etree
from datetime import date
from iso639 import languages

COLLECTION_DISPLAY_NAME = 'Europeana newspapers full-text'

CMD_NS = 'http://www.clarin.eu/cmd/1'
CMDP_NS = 'http://www.clarin.eu/cmd/1/profiles/clarin.eu:cr1:p_1633000337997'

EDM_NAMESPACES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'ore': 'http://www.openarchives.org/ore/terms/',
    'edm': 'http://www.europeana.eu/schemas/edm/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
}

CMD_NAMESPACES = {
    'cmd': CMD_NS,
    'cmdp': CMDP_NS
}

ALL_NAMESPACES = {**EDM_NAMESPACES, **CMD_NAMESPACES}

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    # 'index' metadata records based on properties
    logger.info("Making index for metadata")
    index = make_md_index(metadata_dir)
    # save index to file in output directory
    logger.info(f"Writing index to file")
    save_index(index, f"{output_dir}/index.json")
    # collect identifiers for fulltext records
    logger.info("Collecting fulltext identifiers")
    fulltext_id_file_map = collect_fulltext_ids(fulltext_dir)
    # generate CMDI for the indexed property combinations
    logger.info(f"Creating CMDI record for items in index in {output_dir}")
    generate_cmdi_records(index, fulltext_id_file_map, fulltext_dir, output_dir)

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
                    identifier = normalize_identifier(identifiers[0])
                    titles = [normalize_title(title)
                              for title in xpath_text_values(doc, '/rdf:RDF/edm:ProvidedCHO/dc:title')]
                    years = [date_to_year(date)
                             for date in xpath_text_values(doc, '/rdf:RDF/edm:ProvidedCHO/dcterms:issued')]

                    add_to_index(identifier, titles, years, md_index, filename)
            except etree.Error as err:
                logger.error(f"Error processing XML document: {err=}")
    return md_index


def add_to_index(identifier, titles, years, index, filename):
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


def generate_cmdi_records(index, fulltext_dict, metadata_dir, fulltext_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.dirname(os.path.realpath(__file__))
    template = etree.parse(f"{script_path}/fulltextresource-template.xml")
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
                cmdi_file = make_cmdi_record(template, title, year, ids, fulltext_dict, metadata_dir)
                etree.indent(cmdi_file, space="  ", level=0)
                etree.cleanup_namespaces(cmdi_file, top_nsmap=ALL_NAMESPACES)
                cmdi_file.write(file_name, encoding='utf-8', pretty_print=True, xml_declaration=True)


def collect_fulltext_ids(fulltext_dir):
    ids = {}
    files = os.listdir(fulltext_dir)
    count = 0
    length = len(files)
    for filename in files:
        if filename.endswith(".xml"):
            count += 1
            file_path = f"{fulltext_dir}/{filename}"
            logger.debug(f"Getting identifier from {file_path} ({count}/{length})")
            identifier = extract_fulltext_record_id(file_path)
            if identifier is not None:
                logger.debug(f"Extracted identifier {identifier}")
                ids[normalize_identifier(identifier)] = filename

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


def make_cmdi_record(template, title, year, ids, fulltext_dict, metadata_dir):
    cmdi_file = copy.deepcopy(template)

    # Metadata headers
    set_metadata_headers(cmdi_file)

    # Resource proxies
    resource_proxies_list = xpath(cmdi_file, '/cmd:CMD/cmd:Resources/cmd:ResourceProxyList')
    if len(resource_proxies_list) != 1:
        logger.error("Expecting exactly one components root element")
    else:
        insert_resource_proxies(resource_proxies_list[0], ids, fulltext_dict)

    # Component section
    components_root = xpath(cmdi_file, '/cmd:CMD/cmd:Components/cmdp:TextResource')
    if len(components_root) != 1:
        logger.error("Expecting exactly one components root element")
    else:
        # load EDM metadata records
        edm_records = load_emd_records(ids, metadata_dir)
        insert_component_content(components_root[0], title, year, edm_records)

    return cmdi_file


def load_emd_records(ids, metadata_dir):
    edm_records = []
    for identifier in ids:
        file_path = f"{metadata_dir}/{ids[identifier]}"
        logger.debug(f"Loading metadata file {file_path}")
        try:
            edm_records += [etree.parse(file_path)]
        except etree.Error as err:
            logger.error(f"Error processing XML document: {err=}")
    return edm_records


def set_metadata_headers(doc):
    creator_header = xpath(doc, '/cmd:CMD/cmd:Header/cmd:MdCreator')
    if creator_header:
        creator_header[0].text = os.path.basename(__file__)

    creation_date_header = xpath(doc, '/cmd:CMD/cmd:Header/cmd:MdCreationDate')
    if creation_date_header:
        creation_date_header[0].text = date.today().strftime("%Y-%m-%d")

    # TODO: SelfLink??

    collection_name_header = xpath(doc, '/cmd:CMD/cmd:Header/cmd:MdCollectionDisplayName')
    if collection_name_header:
        collection_name_header[0].text = COLLECTION_DISPLAY_NAME




def insert_resource_proxies(resource_proxies_list, ids, fulltext_dict):
    index = 0
    for identifier in ids:
        proxy_node = etree.SubElement(resource_proxies_list, '{' + CMD_NS + '}ResourceProxy', nsmap=CMD_NAMESPACES)
        proxy_node.attrib['id'] = xml_id(identifier)

        resource_type_node = etree.SubElement(proxy_node, '{' + CMD_NS + '}ResourceType', nsmap=CMD_NAMESPACES)
        resource_type_node.text = "Resource"
        # TODO: resolve to base URL for full text resources!!!
        resource_ref_node = etree.SubElement(proxy_node, '{' + CMD_NS + '}ResourceRef', nsmap=CMD_NAMESPACES)
        resource_ref_node.text = fulltext_dict[identifier]


def insert_component_content(components_root, title, year, edm_records):
    # Title and description
    insert_title_and_description(components_root, title, year)
    # Resource type
    insert_keywords(components_root, edm_records)
    # Publisher
    insert_publisher(components_root, edm_records)
    # Language information
    insert_languages(components_root, edm_records)
    # Temporal coverage
    insert_temporal_coverage(components_root, year)
    # Licence information
    insert_licences(components_root, edm_records)
    # Subresources
    insert_subresource_info(components_root, edm_records)


def insert_title_and_description(parent, title, year):
    # Add title info
    title_info_node = etree.SubElement(parent, '{' + CMDP_NS + '}TitleInfo', nsmap=CMD_NAMESPACES)
    title_node = etree.SubElement(title_info_node, '{' + CMDP_NS + '}title', nsmap=CMD_NAMESPACES)
    title_node.text = f"{title} - {year}"

    # Add description
    description_info_node = etree.SubElement(parent, '{' + CMDP_NS + '}Description', nsmap=CMD_NAMESPACES)
    description_node = etree.SubElement(description_info_node, '{' + CMDP_NS + '}description', nsmap=CMD_NAMESPACES)
    description_node.text = f"Full text content aggregated from Europeana. Title: {title} - {year}"

    # Add resource type ('Text')
    resource_type_node = etree.SubElement(parent, '{' + CMDP_NS + '}ResourceType', nsmap=CMD_NAMESPACES)
    resource_type_label_node = etree.SubElement(resource_type_node, '{' + CMDP_NS + '}label', nsmap=CMD_NAMESPACES)
    resource_type_label_node.text = "Text"


def insert_keywords(parent, edm_records):
    # include dc:type values as keyword
    keywords = get_unique_xpath_values(edm_records, '/rdf:RDF/edm:ProvidedCHO/dc:type/text()')
    for keyword in keywords:
        keyword_node = etree.SubElement(parent, '{' + CMDP_NS + '}Keyword', nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(keyword_node, '{' + CMDP_NS + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = keyword


def insert_publisher(parent, edm_records):
    publishers = get_unique_xpath_values(edm_records,
                                         '/rdf:RDF/ore:Aggregation/edm:dataProvider/text()'
                                         '|/rdf:RDF/ore:Aggregation/edm:provider/text()')
    for publisher in publishers:
        keyword_node = etree.SubElement(parent, '{' + CMDP_NS + '}Publisher', nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(keyword_node, '{' + CMDP_NS + '}name', nsmap=CMD_NAMESPACES)
        label_node.text = publisher


def insert_languages(parent, edm_records):
    language_codes = get_unique_xpath_values(edm_records, '/rdf:RDF/edm:ProvidedCHO/dc:language/text()')
    for language_code in language_codes:
        create_language_component(parent, language_code)


def insert_temporal_coverage(parent, year):
    temporal_coverage_node = etree.SubElement(parent, '{' + CMDP_NS + '}TemporalCoverage',
                                              nsmap=CMD_NAMESPACES)
    label_node = etree.SubElement(temporal_coverage_node, '{' + CMDP_NS + '}label', nsmap=CMD_NAMESPACES)
    label_node.text = year
    start_year = etree.SubElement(etree.SubElement(
        temporal_coverage_node, '{' + CMDP_NS + '}Start', nsmap=CMD_NAMESPACES),
        '{' + CMDP_NS + '}year', nsmap=CMD_NAMESPACES)
    start_year.text = year
    end_year = etree.SubElement(etree.SubElement(
        temporal_coverage_node, '{' + CMDP_NS + '}End', nsmap=CMD_NAMESPACES),
        '{' + CMDP_NS + '}year', nsmap=CMD_NAMESPACES)
    end_year.text = year


def insert_licences(parent, edm_records):
    rights_urls = get_unique_xpath_values(edm_records, '/rdf:RDF/ore:Aggregation/edm:rights/@rdf:resource')
    if len(rights_urls) > 0:
        access_info_node = etree.SubElement(parent, '{' + CMDP_NS + '}AccessInfo', nsmap=CMD_NAMESPACES)
        for rights_url in rights_urls:
            licence_node = etree.SubElement(access_info_node, '{' + CMDP_NS + '}Licence', nsmap=CMD_NAMESPACES)
            identifier_node = etree.SubElement(licence_node, '{' + CMDP_NS + '}identifier', nsmap=CMD_NAMESPACES)
            identifier_node.text = rights_url
            label_node = etree.SubElement(licence_node, '{' + CMDP_NS + '}label', nsmap=CMD_NAMESPACES)
            label_node.text = rights_url
            url_node = etree.SubElement(licence_node, '{' + CMDP_NS + '}url', nsmap=CMD_NAMESPACES)
            url_node.text = rights_url


def insert_subresource_info(components_root, edm_records):
    for record in edm_records:
        identifiers = get_unique_xpath_values([record], '/rdf:RDF/edm:ProvidedCHO/dc:identifier/text()')
        language_codes = get_unique_xpath_values([record], '/rdf:RDF/edm:ProvidedCHO/dc:language/text()')

        subresource_node = etree.SubElement(components_root, '{' + CMDP_NS + '}Subresource', nsmap=CMD_NAMESPACES)
        subresource_description_node = etree.SubElement(subresource_node, '{' + CMDP_NS + '}SubresourceDescription',
                                                        nsmap=CMD_NAMESPACES)
        for title in get_unique_xpath_values([record], '/rdf:RDF/edm:ProvidedCHO/dc:title/text()'):
            label_node = etree.SubElement(subresource_description_node, '{' + CMDP_NS + '}label', nsmap=CMD_NAMESPACES)
            label_node.text = title
        for description in get_unique_xpath_values([record], '/rdf:RDF/edm:ProvidedCHO/dcterms:extent/text()'
                                                             '|/rdf:RDF/edm:ProvidedCHO/dc:type/text()'):
            description_node = etree.SubElement(subresource_description_node,
                                                '{' + CMDP_NS + '}description', nsmap=CMD_NAMESPACES)
            description_node.text = description
        if len(identifiers) > 0:
            subresource_node.attrib['{' + CMD_NS + '}ref'] = xml_id(normalize_identifier(identifiers[0]))
            identification_info_node = etree.SubElement(subresource_description_node,
                                                        '{' + CMDP_NS + '}IdentificationInfo', nsmap=CMD_NAMESPACES)
            for identifier in identifiers:
                identifier_node = etree.SubElement(identification_info_node, '{' + CMDP_NS + '}identifier',
                                                   nsmap=CMD_NAMESPACES)
                identifier_node.text = identifier
        for language_code in language_codes:
            create_language_component(subresource_description_node, language_code)
        for issued_date in get_unique_xpath_values([record], '/rdf:RDF/edm:ProvidedCHO/dcterms:issued/text()'):
            if is_valid_date(issued_date):
                temporal_coverage_node = etree.SubElement(subresource_description_node,
                                                          '{' + CMDP_NS + '}TemporalCoverage',
                                                          nsmap=CMD_NAMESPACES)
                label_node = etree.SubElement(temporal_coverage_node, '{' + CMDP_NS + '}label', nsmap=CMD_NAMESPACES)
                label_node.text = issued_date


def create_language_component(parent, language_code):
    language_node = etree.SubElement(parent, '{' + CMDP_NS + '}Language', nsmap=CMD_NAMESPACES)
    language_name_node = etree.SubElement(language_node, '{' + CMDP_NS + '}name', nsmap=CMD_NAMESPACES)
    language = None
    if len(language_code) == 2:
        # lookup 639-1 code to get name + 3 letter code
        language = languages.get(alpha2=language_code)
    if len(language_code) == 3:
        # lookup for 3 letter code
        language = languages.get(part3=language_code)
    if language is None:
        language_name_node.text = language_code
    else:
        language_name_node.text = language.name
        language_code_node = etree.SubElement(language_node, '{' + CMDP_NS + '}code', nsmap=CMD_NAMESPACES)
        language_code_node.text = language.part3


def get_unique_xpath_values(docs, path):
    return list(dict.fromkeys(get_all_xpath_values(docs, path)))


def get_all_xpath_values(docs, path):
    values = []
    for doc in docs:
        values += xpath(doc, path)
    return values


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


def normalize_identifier(identifier):
    # ex. http://data.theeuropeanlibrary.org/BibliographicResource/3000118435146
    # ex. http://data.europeana.eu/annotation/9200396/BibliographicResource_3000118435009
    match = re.search(r"http.*[^\d](\d+)$", identifier)
    if match:
        logger.debug(f"Normalised identifier: {identifier} -> {match.group(1)}")
        return match.group(1)
    else:
        logger.warning(f"Identifier {identifier} does not match pattern, skipping normalisation!")
        return identifier


def xml_id(identifier):
    new_id = identifier
    if not re.match(r"^[A-z_]", identifier):
        new_id = "_" + identifier
    return re.sub('[^A-z0-9_]', '_', new_id)


def date_to_year(date):
    match = re.search(r"(\d{4})-\d{2}-\d{2}", date)
    if match:
        return match.group(1)
    else:
        return None


def is_valid_date(date):
    return re.match(r"(^\d{4})-\d{2}-\d{2}$", date) is not None


def normalize_title(title):
    match = re.search(r"^[A-z0-9'\"()\s]*[A-z0-9'\"()]", unidecode.unidecode(title))
    if match:
        return title[match.start(0):match.end(0)]
    else:
        return None


def filename_safe(name):
    return re.sub(r"[^A-z0-9]", '_', name)


# -- test runs


def test_run():
    index = {
        "La clef du cabinet des princes de l'Europe": {
            "1716": {
                "3000118435146": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435146.edm.xml",
                "3000118435156": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435156.edm.xml",
                "3000118435157": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435157.edm.xml",
                "3000118435147": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435147.edm.xml",
                "3000118435155": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435155.edm.xml",
                "3000118435154": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435154.edm.xml",
                "3000118435158": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435158.edm.xml",
                "3000118435148": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435148.edm.xml",
                "3000118435150": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435150.edm.xml",
                "3000118435149": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435149.edm.xml",
                "3000118435152": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435152.edm.xml",
                "3000118435153": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118435153.edm.xml"
            }
        }, "Journal historique et litt\u00e9raire": {
            "1790": {
                "3000118436032": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436032.edm.xml",
                "3000118436022": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436022.edm.xml",
                "3000118436014": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436014.edm.xml",
                "3000118436015": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436015.edm.xml",
                "3000118436023": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436023.edm.xml",
                "3000118436033": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436033.edm.xml",
                "3000118436028": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436028.edm.xml",
                "3000118436017": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436017.edm.xml",
                "3000118436031": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436031.edm.xml",
                "3000118436021": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436021.edm.xml",
                "3000118436020": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436020.edm.xml",
                "3000118436030": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436030.edm.xml",
                "3000118436029": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436029.edm.xml",
                "3000118436016": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436016.edm.xml",
                "3000118436013": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436013.edm.xml",
                "3000118436035": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436035.edm.xml",
                "3000118436025": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436025.edm.xml",
                "3000118436024": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436024.edm.xml",
                "3000118436034": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436034.edm.xml",
                "3000118436019": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436019.edm.xml",
                "3000118436036": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436036.edm.xml",
                "3000118436026": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436026.edm.xml",
                "3000118436018": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436018.edm.xml",
                "3000118436027": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436027.edm.xml"
            },
            "1779": {
                "3000118436295": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436295.edm.xml",
                "3000118436285": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436285.edm.xml",
                "3000118436300": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436300.edm.xml",
                "3000118436278": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436278.edm.xml",
                "3000118436279": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436279.edm.xml",
                "3000118436284": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436284.edm.xml",
                "3000118436294": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436294.edm.xml",
                "3000118436296": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436296.edm.xml",
                "3000118436286": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436286.edm.xml",
                "3000118436287": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436287.edm.xml",
                "3000118436297": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436297.edm.xml",
                "3000118436292": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436292.edm.xml",
                "3000118436282": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436282.edm.xml",
                "3000118436277": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436277.edm.xml",
                "3000118436283": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436283.edm.xml",
                "3000118436293": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436293.edm.xml",
                "3000118436291": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436291.edm.xml",
                "3000118436281": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436281.edm.xml",
                "3000118436288": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436288.edm.xml",
                "3000118436298": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436298.edm.xml",
                "3000118436299": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436299.edm.xml",
                "3000118436289": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436289.edm.xml",
                "3000118436280": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436280.edm.xml",
                "3000118436290": "http%3A%2F%2Fdata.theeuropeanlibrary.org%2FBibliographicResource%2F3000118436290.edm.xml"
            }
        }
    }
    fulltext_ids = {
        '3000118435146': 'BibliographicResource_3000118435146.xml',
        '3000118436295': 'BibliographicResource_3000118436295.xml',
        '3000118436279': 'BibliographicResource_3000118436279.xml'
    }
    generate_cmdi_records(index, fulltext_ids,
                          metadata_dir='/Users/twagoo/Documents/Projects/Europeana/fulltext/dumps/edm-md/9200396',
                          fulltext_dir='/Users/twagoo/Documents/Projects/Europeana/fulltext/dumps/edm-issue/9200396',
                          output_dir='./test-output')


if __name__ == "__main__":
    test_run()
