import logging
import os
import json
import pprint
import re

import glom as gl
from glom import glom, SKIP

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir, properties):
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
                    publishers = get_value_from_proxies(metadata, 'dcPublisher')
                    issued_dates = get_value_from_proxies(metadata, 'dctermsIssued')
                    issued_years = [date_to_year(date) for date in issued_dates]
                    logger.debug(f"Identifier: {identifier}; Publisher: {publishers}; Issued: {issued_dates}")

                    for publisher in publishers:
                        if publisher not in index:
                            index[publisher] = {}
                        for year in issued_years:
                            if year not in index[publisher]:
                                index[publisher][year] = []
                            index[publisher][year] += [identifier]
    pprint.pprint(index)
    # TODO: generate metadata for property combinations


def get_value_from_proxies(metadata, prop):
    try:
        glom_spec = (
            'proxies',
            [lambda x: glom(x, prop, default=SKIP)],
            ['def']
        )
        return gl.flatten(glom(metadata, glom_spec, default=None))
    except gl.core.PathAccessError:
        logger.warning("Publisher not found")


def date_to_year(date):
    logger.debug(f"Date: {date}")
    match = re.search(r"(\d{4})-\d{2}-\d{2}", date)
    if match:
        return match.group(1)
    else:
        return None
