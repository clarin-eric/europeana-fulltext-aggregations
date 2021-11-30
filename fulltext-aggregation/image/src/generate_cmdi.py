import logging
import os
import json
import unidecode
import re

import glom as gl
from glom import glom, SKIP

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir, output_filename='output.json'):
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    # 'index' metadata records based on properties
    index = {}

    logger.debug(f"Reading metadata from {metadata_dir}")
    for filename in os.listdir(metadata_dir):
        if filename.endswith(".json"):
            file_path = f"{metadata_dir}/{filename}"
            with open(file_path) as file:
                metadata = json.load(file).get("object", None)
                if metadata is None:
                    logger.error(f"Metadata object could not be read from {file_path}")
                else:
                    identifier = metadata['about']
                    titles = get_value_from_proxies(metadata, 'dcTitle')
                    normalized_titles = [normalize_title(title) for title in titles]
                    issued_dates = get_value_from_proxies(metadata, 'dctermsIssued')
                    issued_years = [date_to_year(date) for date in issued_dates]
                    logger.debug(f"Identifier: {identifier}; Title: {titles}; Issued: {issued_dates}")

                    for title in normalized_titles:
                        if title not in index:
                            index[title] = {}
                        for year in issued_years:
                            if year not in index[title]:
                                index[title][year] = []
                            index[title][year] += [identifier]

    with open(output_filename, 'w') as output_file:
        json.dump(index, output_file, indent=True)

    # TODO: generate CMDI for property combinations
    # only for records that have full-text!


def get_value_from_proxies(metadata, prop):
    try:
        glom_spec = (
            'proxies',
            [lambda x: glom(x, prop, default=SKIP)],
            ['def']
        )
        return gl.flatten(glom(metadata, glom_spec, default=None))
    except gl.core.PathAccessError:
        logger.warning("Property not found")


def date_to_year(date):
    match = re.search(r"(\d{4})-\d{2}-\d{2}", date)
    if match:
        return match.group(1)
    else:
        return None


def normalize_title(title):
    match = re.search(r"^[a-zA-Z ]+", unidecode.unidecode(title))
    if match:
        return title[match.start(0):match.end(0)]
    else:
        return None

