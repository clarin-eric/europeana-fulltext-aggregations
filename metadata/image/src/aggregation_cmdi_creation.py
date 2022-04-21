import logging
import os

from copy import deepcopy
from datetime import date
from iso639 import languages
from lxml import etree

from common import CMD_NS, CMDP_NS_RECORD, CMDP_NS_COLLECTION_RECORD, CMD_NAMESPACES
from common import xpath, get_unique_xpath_values
from common import normalize_identifier, xml_id, is_valid_date
from env import COLLECTION_DISPLAY_NAME, LANDING_PAGE_URL, CMDI_RECORDS_BASE_URL, PRETTY_CMDI_XML

LANDING_PAGE_ID = 'landing_page'
EDM_DUMP_PROXY_ID = 'archive_edm'
ALTO_DUMP_PROXY_ID = 'archive_alto'
DUMP_MEDIA_TYPE = 'application/zip'
RECORD_PAGE_MEDIA_TYPE = 'text/html'
FULL_TEXT_RECORD_TEMPLATE_FILE = 'fulltextresource-template.xml'
COLLECTION_RECORD_TEMPLATE_FILE = 'collectionrecord-template.xml'

logger = logging.getLogger(__name__)
parser = etree.XMLParser(remove_blank_text=not PRETTY_CMDI_XML)


def make_template(filename):
    script_path = os.path.dirname(os.path.realpath(__file__))
    return etree.parse(f"{script_path}/{filename}", parser)


def make_cmdi_template():
    return make_template(FULL_TEXT_RECORD_TEMPLATE_FILE)


def make_collection_record_template():
    return make_template(COLLECTION_RECORD_TEMPLATE_FILE)


def make_cmdi_record(record_file_name, template, collection_id, title, year, records_map, metadata_dir):
    cmdi_file = deepcopy(template)

    # load EDM metadata records
    edm_records = load_emd_records(records_map, metadata_dir)

    # Metadata headers
    set_metadata_headers(cmdi_file, collection_id, record_file_name)

    # Resource proxies
    resource_proxies_list = xpath(cmdi_file, '/cmd:CMD/cmd:Resources/cmd:ResourceProxyList')
    if len(resource_proxies_list) != 1:
        logger.error("Expecting exactly one components root element")
        return None
    else:
        insert_resource_proxies(resource_proxies_list[0], collection_id, edm_records)

    # Component section
    components_root = xpath(cmdi_file, f"/cmd:CMD/cmd:Components/cmdp:TextResource")
    if len(components_root) != 1:
        logger.error("Expecting exactly one components root element")
        return None
    else:
        # insert component content
        insert_component_content(components_root[0], title, year, edm_records)

    return cmdi_file


def load_emd_records(records_map, metadata_dir):
    edm_records = []
    for identifier in records_map:
        file_name = records_map[identifier].get('file', None)
        if file_name is None:
            logger.error(f"No file name in records map for {identifier}")
        else:
            file_path = f"{metadata_dir}/{file_name}"
            logger.debug(f"Loading metadata file {file_path}")
            try:
                edm_records += [etree.parse(file_path)]
            except etree.Error as err:
                logger.error(f"Error processing XML document: {err=}")
    return edm_records


def set_metadata_headers(doc, collection_id, record_file_name):
    creator_header = xpath(doc, '/cmd:CMD/cmd:Header/cmd:MdCreator')
    if creator_header:
        creator_header[0].text = os.path.basename(__file__)

    creation_date_header = xpath(doc, '/cmd:CMD/cmd:Header/cmd:MdCreationDate')
    if creation_date_header:
        creation_date_header[0].text = today_string()

    selflink_header = xpath(doc, '/cmd:CMD/cmd:Header/cmd:MdSelfLink')
    if creation_date_header:
        selflink_header[0].text = f"{CMDI_RECORDS_BASE_URL}/{collection_id}/{record_file_name}"

    collection_name_header = xpath(doc, '/cmd:CMD/cmd:Header/cmd:MdCollectionDisplayName')
    if collection_name_header:
        collection_name_header[0].text = COLLECTION_DISPLAY_NAME


def insert_resource_proxies(resource_proxies_list, collection_id, edm_records):
    # landing page
    insert_resource_proxy(resource_proxies_list, LANDING_PAGE_ID, "LandingPage", LANDING_PAGE_URL)

    # dump URLs
    insert_resource_proxy(resource_proxies_list, EDM_DUMP_PROXY_ID, "Resource",
                          make_edm_dump_ref(collection_id), DUMP_MEDIA_TYPE)
    insert_resource_proxy(resource_proxies_list, ALTO_DUMP_PROXY_ID, "Resource",
                          make_alto_dump_ref(collection_id), DUMP_MEDIA_TYPE)

    # record landing pages
    for record_page_ref in get_unique_xpath_values(
            edm_records, '/rdf:RDF/edm:EuropeanaAggregation/edm:landingPage/@rdf:resource'):
        insert_resource_proxy(resource_proxies_list, make_record_page_ref(record_page_ref), "Resource",
                              record_page_ref, RECORD_PAGE_MEDIA_TYPE)


def insert_resource_proxy(parent, proxy_id, resource_type, ref, media_type=None):
    proxy_node = etree.SubElement(parent, '{' + CMD_NS + '}ResourceProxy', nsmap=CMD_NAMESPACES)
    proxy_node.attrib['id'] = proxy_id
    resource_type_node = etree.SubElement(proxy_node, '{' + CMD_NS + '}ResourceType', nsmap=CMD_NAMESPACES)
    resource_type_node.text = resource_type
    resource_ref_node = etree.SubElement(proxy_node, '{' + CMD_NS + '}ResourceRef', nsmap=CMD_NAMESPACES)
    resource_ref_node.text = ref

    if media_type is not None:
        resource_type_node.attrib['mimetype'] = media_type


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
    # Countries
    insert_countries(components_root, edm_records)
    # Licence information
    insert_licences(components_root, edm_records)
    # Subresources
    insert_subresource_info(components_root, edm_records)
    # Metadata information
    insert_metadata_info(components_root)


def insert_title_and_description(parent, title, year):
    # Add title info
    title_info_node = etree.SubElement(parent, '{' + CMDP_NS_RECORD + '}TitleInfo', nsmap=CMD_NAMESPACES)
    title_node = etree.SubElement(title_info_node, '{' + CMDP_NS_RECORD + '}title', nsmap=CMD_NAMESPACES)
    title_node.text = f"{title} - {year}"

    # Add description
    description_info_node = etree.SubElement(parent, '{' + CMDP_NS_RECORD + '}Description', nsmap=CMD_NAMESPACES)
    description_node = etree.SubElement(description_info_node, '{' + CMDP_NS_RECORD + '}description',
                                        nsmap=CMD_NAMESPACES)
    description_node.text = f"Full text content aggregated from Europeana. Title: \"{title}\". Year: {year}."

    # Add resource type ('Text')
    resource_type_node = etree.SubElement(parent, '{' + CMDP_NS_RECORD + '}ResourceType', nsmap=CMD_NAMESPACES)
    resource_type_label_node = etree.SubElement(resource_type_node, '{' + CMDP_NS_RECORD + '}label',
                                                nsmap=CMD_NAMESPACES)
    resource_type_label_node.text = "Text"


def insert_keywords(parent, edm_records, namespace=CMDP_NS_RECORD):
    # include dc:type values as keyword
    keywords = get_unique_xpath_values(edm_records, '/rdf:RDF/ore:Proxy/dc:type/text()')
    for keyword in keywords:
        keyword_node = etree.SubElement(parent, '{' + namespace + '}Keyword', nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(keyword_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = keyword


def insert_publisher(parent, edm_records, namespace=CMDP_NS_RECORD):
    publishers = get_unique_xpath_values(edm_records,
                                         '/rdf:RDF/ore:Aggregation/edm:dataProvider/text()'
                                         '|/rdf:RDF/ore:Aggregation/edm:provider/text()')
    for publisher in publishers:
        keyword_node = etree.SubElement(parent, '{' + namespace + '}Publisher', nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(keyword_node, '{' + namespace + '}name', nsmap=CMD_NAMESPACES)
        label_node.text = publisher


def insert_languages(parent, edm_records, namespace=CMDP_NS_RECORD):
    language_codes = get_unique_xpath_values(edm_records, '/rdf:RDF/ore:Proxy/dc:language/text()')
    for language_code in language_codes:
        create_language_component(parent, language_code, namespace)


def insert_temporal_coverage(parent, year):
    temporal_coverage_node = etree.SubElement(parent, '{' + CMDP_NS_RECORD + '}TemporalCoverage',
                                              nsmap=CMD_NAMESPACES)
    label_node = etree.SubElement(temporal_coverage_node, '{' + CMDP_NS_RECORD + '}label', nsmap=CMD_NAMESPACES)
    label_node.text = year
    start_year = etree.SubElement(etree.SubElement(
        temporal_coverage_node, '{' + CMDP_NS_RECORD + '}Start', nsmap=CMD_NAMESPACES),
        '{' + CMDP_NS_RECORD + '}year', nsmap=CMD_NAMESPACES)
    start_year.text = year
    end_year = etree.SubElement(etree.SubElement(
        temporal_coverage_node, '{' + CMDP_NS_RECORD + '}End', nsmap=CMD_NAMESPACES),
        '{' + CMDP_NS_RECORD + '}year', nsmap=CMD_NAMESPACES)
    end_year.text = year


def insert_countries(parent, edm_record, namespace=CMDP_NS_RECORD):
    countries = get_unique_xpath_values(edm_record, '/rdf:RDF/edm:EuropeanaAggregation/edm:country/text()')
    for country in countries:
        geolocation_node = etree.SubElement(parent, '{' + namespace + '}GeoLocation', nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(geolocation_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = country
        country_node = etree.SubElement(geolocation_node, '{' + namespace + '}Country', nsmap=CMD_NAMESPACES)
        country_label_node = etree.SubElement(country_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        country_label_node.text = country


def insert_licences(parent, edm_records, namespace=CMDP_NS_RECORD):
    rights_urls = get_unique_xpath_values(edm_records, '/rdf:RDF/ore:Aggregation/edm:rights/@rdf:resource')
    if len(rights_urls) > 0:
        access_info_node = etree.SubElement(parent, '{' + namespace + '}AccessInfo', nsmap=CMD_NAMESPACES)
        for rights_url in rights_urls:
            licence_node = etree.SubElement(access_info_node, '{' + namespace + '}Licence', nsmap=CMD_NAMESPACES)
            identifier_node = etree.SubElement(licence_node, '{' + namespace + '}identifier', nsmap=CMD_NAMESPACES)
            identifier_node.text = rights_url
            label_node = etree.SubElement(licence_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
            label_node.text = rights_url
            url_node = etree.SubElement(licence_node, '{' + namespace + '}url', nsmap=CMD_NAMESPACES)
            url_node.text = rights_url


def insert_subresource_info(components_root, edm_records, namespace=CMDP_NS_RECORD):
    insert_dump_subresource_info(components_root, namespace)
    # info for each issue (record)
    for record in edm_records:
        insert_issue_subresource_info(components_root, record, namespace)


def insert_issue_subresource_info(parent, record, namespace=CMDP_NS_RECORD):
    subresource_node = etree.SubElement(parent, '{' + namespace + '}Subresource', nsmap=CMD_NAMESPACES)
    subresource_description_node = etree.SubElement(subresource_node,
                                                    '{' + namespace + '}SubresourceDescription',
                                                    nsmap=CMD_NAMESPACES)

    # proxy ref
    record_page_ref = get_unique_xpath_values(
        [record], '/rdf:RDF/edm:EuropeanaAggregation/edm:landingPage/@rdf:resource')
    if len(record_page_ref) > 0:
        subresource_node.attrib['{' + CMD_NS + '}ref'] = make_record_page_ref(record_page_ref[0])

    # title info
    for title in get_unique_xpath_values([record], '/rdf:RDF/ore:Proxy/dc:title/text()'):
        label_node = etree.SubElement(subresource_description_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = f"{title}"

    # identifier(s)
    for identifier in get_unique_xpath_values([record], '/rdf:RDF/ore:Proxy/dc:identifier/text()'):
        identification_info_node = etree.SubElement(subresource_description_node,
                                                    '{' + namespace + '}IdentificationInfo',
                                                    nsmap=CMD_NAMESPACES)

        normalized_id = normalize_identifier(identifier)
        if identifier != normalized_id:
            identifier_node = etree.SubElement(identification_info_node, '{' + namespace + '}identifier',
                                               nsmap=CMD_NAMESPACES)
            identifier_node.text = identifier
        identifier_node = etree.SubElement(identification_info_node, '{' + namespace + '}identifier',
                                           nsmap=CMD_NAMESPACES)
        identifier_node.text = normalized_id

    # languages
    for language_code in get_unique_xpath_values([record], '/rdf:RDF/ore:Proxy/dc:language/text()'):
        create_language_component(subresource_description_node, language_code, namespace)

    # temporal coverage
    for issue_date in get_unique_xpath_values([record], '/rdf:RDF/ore:Proxy/dcterms:issued/text()'):
        temporal_coverage_node = etree.SubElement(subresource_description_node, '{' + namespace + '}TemporalCoverage',
                                                  nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(temporal_coverage_node, '{' + namespace + '}label',
                                      nsmap=CMD_NAMESPACES)
        label_node.text = issue_date
        if is_valid_date(issue_date):
            start = etree.SubElement(etree.SubElement(
                temporal_coverage_node, '{' + namespace + '}Start', nsmap=CMD_NAMESPACES),
                '{' + namespace + '}date', nsmap=CMD_NAMESPACES)
            start.text = issue_date
            end = etree.SubElement(etree.SubElement(
                temporal_coverage_node, '{' + namespace + '}End', nsmap=CMD_NAMESPACES),
                '{' + namespace + '}date', nsmap=CMD_NAMESPACES)
            end.text = issue_date

    # geolocation
    for country in get_unique_xpath_values([record], '/rdf:RDF/edm:EuropeanaAggregation/edm:country/text()'):
        geolocation_node = etree.SubElement(subresource_description_node, '{' + namespace + '}GeoLocation',
                                            nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(geolocation_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = country
        country_node = etree.SubElement(geolocation_node, '{' + namespace + '}Country', nsmap=CMD_NAMESPACES)
        country_label_node = etree.SubElement(country_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        country_label_node.text = country


def insert_dump_subresource_info(parent, namespace=CMDP_NS_RECORD):
    for dump in [(EDM_DUMP_PROXY_ID,
                  'Archive containing full text content in EDM format which includes this title'),
                 (ALTO_DUMP_PROXY_ID,
                  'Archive containing full text content in ALTO format which includes this title')]:
        subresource_node = etree.SubElement(parent, '{' + namespace + '}Subresource', nsmap=CMD_NAMESPACES)
        subresource_description_node = etree.SubElement(subresource_node,
                                                        '{' + namespace + '}SubresourceDescription',
                                                        nsmap=CMD_NAMESPACES)
        subresource_node.attrib['{' + CMD_NS + '}ref'] = dump[0]
        label_node = etree.SubElement(subresource_description_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = dump[1]


def create_language_component(parent, language_code, namespace=CMDP_NS_RECORD):
    language_node = etree.SubElement(parent, '{' + namespace + '}Language', nsmap=CMD_NAMESPACES)
    language_name_node = etree.SubElement(language_node, '{' + namespace + '}name', nsmap=CMD_NAMESPACES)
    language = None

    try:
        if len(language_code) == 2:
            # lookup 639-1 code to get name + 3 letter code
            language = languages.get(alpha2=language_code)
        if len(language_code) == 3:
            # lookup for 3 letter code
            language = languages.get(part3=language_code)
    except KeyError:
        logger.warning(f"Language name lookup failed: no code '{language_code}' in dictionary")
    if language is None:
        language_name_node.text = language_code
    else:
        language_name_node.text = language.name
        language_code_node = etree.SubElement(language_node, '{' + namespace + '}code', nsmap=CMD_NAMESPACES)
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
                  <note>Metadata and full text retrieved from Europeana servers.
                  See https://pro.europeana.eu/page/iiif#download</note>
                  <When>
                    <label>2021</label>
                    <year>2021</year>
                  </When>
                </ActivityInfo>
              </Collection>
            </ProvenanceInfo>
          </MetadataInfo>
        ''', parser=parser)
    parent.insert(len(parent), metadata_info)

# ###################
# Collection records
# ###################


def make_collection_record(file_name, template, collection_id, title, year_files, input_record_map, metadata_dir):
    cmdi_file = deepcopy(template)

    # Metadata headers
    set_metadata_headers(cmdi_file, collection_id, file_name)

    # Resource proxies
    resource_proxies_list = xpath(cmdi_file, '/cmd:CMD/cmd:Resources/cmd:ResourceProxyList')
    if len(resource_proxies_list) != 1:
        logger.error("Expecting exactly one components root element")
        return None
    else:
        collection_insert_resource_proxies(resource_proxies_list[0], year_files, collection_id)

    # Component section
    components_root = xpath(cmdi_file, f"/cmd:CMD/cmd:Components/cmdp_c:MetadataCollection")
    if len(components_root) != 1:
        logger.error("Expecting exactly one components root element")
        return None
    else:
        # load EDM metadata records
        edm_records = load_emd_records(input_record_map, metadata_dir)
        # insert component content
        collection_insert_component_content(components_root[0], title, sorted(list(year_files)),
                                            year_files, edm_records)

    return cmdi_file


def collection_insert_resource_proxies(resource_proxies_list, year_files, collection_id):
    # landing page
    insert_resource_proxy(resource_proxies_list, LANDING_PAGE_ID, "LandingPage", LANDING_PAGE_URL)

    # dump URLs
    insert_resource_proxy(resource_proxies_list, EDM_DUMP_PROXY_ID, "Resource",
                          make_edm_dump_ref(collection_id), DUMP_MEDIA_TYPE)
    insert_resource_proxy(resource_proxies_list, ALTO_DUMP_PROXY_ID, "Resource",
                          make_alto_dump_ref(collection_id), DUMP_MEDIA_TYPE)

    # links to metadata records
    for year in sorted(year_files):
        file_name = year_files[year]
        ref = f"{CMDI_RECORDS_BASE_URL}/{collection_id}/{file_name}"
        insert_resource_proxy(resource_proxies_list, xml_id(year), "Metadata", ref)


def collection_insert_component_content(components_root, title, sorted_years, year_files, input_records):
    # Title and description
    collection_insert_title_and_description(components_root, title, sorted_years)
    # Resource type
    insert_keywords(components_root, input_records, CMDP_NS_COLLECTION_RECORD)
    # Publisher
    insert_publisher(components_root, input_records, CMDP_NS_COLLECTION_RECORD)
    # Language information
    insert_languages(components_root, input_records, CMDP_NS_COLLECTION_RECORD)
    # Temporal coverage
    collection_insert_temporal_coverage(components_root, sorted_years[0], sorted_years[-1])
    # Countries
    insert_countries(components_root, input_records, CMDP_NS_COLLECTION_RECORD)
    # Licence information
    insert_licences(components_root, input_records, CMDP_NS_COLLECTION_RECORD)
    # # Subresources
    collection_insert_subresource_info(components_root, title, year_files)
    # TODO: subresource info for dumps (ALTO and EDM)
    # Metadata information
    insert_metadata_info(components_root)


def collection_insert_title_and_description(parent, title, years):
    # Add title info
    title_info_node = etree.SubElement(parent, '{' + CMDP_NS_COLLECTION_RECORD + '}TitleInfo',
                                       nsmap=CMD_NAMESPACES)
    title_node = etree.SubElement(title_info_node, '{' + CMDP_NS_COLLECTION_RECORD + '}title',
                                  nsmap=CMD_NAMESPACES)
    title_node.text = f"{title}"

    # Add description
    description_info_node = etree.SubElement(parent, '{' + CMDP_NS_COLLECTION_RECORD + '}Description',
                                             nsmap=CMD_NAMESPACES)
    description_node = etree.SubElement(description_info_node, '{' + CMDP_NS_COLLECTION_RECORD + '}description',
                                        nsmap=CMD_NAMESPACES)
    description_node.text = f"Full text content aggregated from Europeana. " \
                            f"Title: \"{title}\". " \
                            f"Years: {', '.join(years)}."

    # Add resource type ('Text')
    resource_type_node = etree.SubElement(parent, '{' + CMDP_NS_COLLECTION_RECORD + '}ResourceType',
                                          nsmap=CMD_NAMESPACES)
    resource_type_label_node = etree.SubElement(resource_type_node, '{' + CMDP_NS_COLLECTION_RECORD + '}label',
                                                nsmap=CMD_NAMESPACES)
    resource_type_label_node.text = "Text"


def collection_insert_temporal_coverage(parent, year_lower, year_higher):
    temporal_coverage_node = etree.SubElement(parent, '{' + CMDP_NS_COLLECTION_RECORD + '}TemporalCoverage',
                                              nsmap=CMD_NAMESPACES)
    label_node = etree.SubElement(temporal_coverage_node, '{' + CMDP_NS_COLLECTION_RECORD + '}label',
                                  nsmap=CMD_NAMESPACES)
    label_node.text = f"{year_lower} - {year_higher}"
    start_year = etree.SubElement(etree.SubElement(
        temporal_coverage_node, '{' + CMDP_NS_COLLECTION_RECORD + '}Start', nsmap=CMD_NAMESPACES),
        '{' + CMDP_NS_COLLECTION_RECORD + '}year', nsmap=CMD_NAMESPACES)
    start_year.text = year_lower
    end_year = etree.SubElement(etree.SubElement(
        temporal_coverage_node, '{' + CMDP_NS_COLLECTION_RECORD + '}End', nsmap=CMD_NAMESPACES),
        '{' + CMDP_NS_COLLECTION_RECORD + '}year', nsmap=CMD_NAMESPACES)
    end_year.text = year_higher


def collection_insert_subresource_info(parent, title, year_files, namespace=CMDP_NS_COLLECTION_RECORD):
    insert_dump_subresource_info(parent, namespace)
    # Subresource info for metadata links
    for year in sorted(year_files):
        subresource_node = etree.SubElement(parent,
                                            '{' + namespace + '}Subresource', nsmap=CMD_NAMESPACES)
        subresource_description_node = etree.SubElement(subresource_node,
                                                        '{' + namespace + '}SubresourceDescription',
                                                        nsmap=CMD_NAMESPACES)
        subresource_node.attrib['{' + CMD_NS + '}ref'] = xml_id(year)
        label_node = etree.SubElement(subresource_description_node,
                                      '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = f"{title} - {year}"
        # Temporal coverage
        temporal_coverage_node = etree.SubElement(subresource_description_node,
                                                  '{' + namespace + '}TemporalCoverage', nsmap=CMD_NAMESPACES)
        label_node = etree.SubElement(temporal_coverage_node, '{' + namespace + '}label', nsmap=CMD_NAMESPACES)
        label_node.text = year


def make_edm_dump_ref(collection_id):
    return f"ftp://download.europeana.eu/newspapers/fulltext/edm_issue/{collection_id}.zip"


def make_alto_dump_ref(collection_id):
    return f"ftp://download.europeana.eu/newspapers/fulltext/alto/{collection_id}.zip"


def make_record_page_ref(page_ref):
    return f"rp_{normalize_identifier(page_ref)}"


def today_string():
    return date.today().strftime("%Y-%m-%d")
