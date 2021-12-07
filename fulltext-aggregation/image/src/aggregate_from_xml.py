import common
import logging
import os
import json
from lxml import etree
from aggregation_cmdi_creation import make_cmdi_record
from common import ALL_NAMESPACES
from common import get_mandatory_env_var, log_progress
from common import xpath_text_values
from common import normalize_title, normalize_identifier, date_to_year, filename_safe

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir, full_text_base_url, output_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

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
    generate_cmdi_records(index, fulltext_id_file_map, metadata_dir, output_dir, full_text_base_url)

    logger.info("Done")


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

            count += 1
            last_log = log_progress(logger, total, count, last_log,
                                    category="Reading metadata files",
                                    interval_pct=10)
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


def generate_cmdi_records(index, fulltext_dict, metadata_dir, output_dir, full_text_base_url):
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
                cmdi_file = make_cmdi_record(template, title, year, ids, fulltext_dict, metadata_dir, full_text_base_url)
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
                          output_dir='./test-output',
                          full_text_base_url='http://www.clarin.eu/europeana/fulltext/9200396/')


if __name__ == "__main__":
    test_run()
