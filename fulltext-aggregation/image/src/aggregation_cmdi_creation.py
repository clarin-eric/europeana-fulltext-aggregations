import logging
import os
import copy
from lxml import etree
from datetime import date
from iso639 import languages
from common import CMD_NS, CMDP_NS, CMD_NAMESPACES
from common import xpath, get_unique_xpath_values
from common import normalize_identifier, xml_id, is_valid_date

COLLECTION_DISPLAY_NAME = 'Europeana newspapers full-text'

logger = logging.getLogger(__name__)


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
        creation_date_header[0].text = today_string()

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
    # Metadata information
    insert_metadata_info(components_root)


def insert_title_and_description(parent, title, year):
    # Add title info
    title_info_node = etree.SubElement(parent, '{' + CMDP_NS + '}TitleInfo', nsmap=CMD_NAMESPACES)
    title_node = etree.SubElement(title_info_node, '{' + CMDP_NS + '}title', nsmap=CMD_NAMESPACES)
    title_node.text = f"{title} - {year}"

    # Add description
    description_info_node = etree.SubElement(parent, '{' + CMDP_NS + '}Description', nsmap=CMD_NAMESPACES)
    description_node = etree.SubElement(description_info_node, '{' + CMDP_NS + '}description', nsmap=CMD_NAMESPACES)
    description_node.text = f"Full text content aggregated from Europeana. Title: \"{title}\". Year: {year}."

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


def insert_metadata_info(parent):
    metadata_info = etree.XML(f'''
        <MetadataInfo>
            <Publisher>
              <name>CLARIN ERIC</name>
              <ContactInfo>
                <url>https://www.clarin.eu</url>
              </ContactInfo>
            </Publisher>
            <ProvenanceInfo>
              <Creation>
                <ActivityInfo>
                  <method>Creation and aggregation by The European Library/Europeana</method>
                  <note>EDM metadata</note>
                  <When>
                    <label>Unspecified</label>
                  </When>
                </ActivityInfo>
                <ActivityInfo>
                  <method>Conversion</method>
                  <note>Converted from EDM to CMDI</note>
                  <When>
                    <date>{today_string()}</date>
                  </When>
                </ActivityInfo>
              </Creation>
              <Collection>
                <ActivityInfo>
                  <method>Aggregation</method>
                  <note>Metadata and full text retrieved from Europeana servers. See https://pro.europeana.eu/page/iiif#download</note>
                  <When>
                    <label>2021</label>
                    <year>2021</year>
                  </When>
                </ActivityInfo>
              </Collection>
            </ProvenanceInfo>
          </MetadataInfo>
        ''')
    parent.insert(len(parent), metadata_info)



def today_string():
    return date.today().strftime("%Y-%m-%d")