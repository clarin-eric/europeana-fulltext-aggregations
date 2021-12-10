import api_retrieval
import generate_cmdi
import aggregate_from_xml
import logging
import sys
from common import get_optional_env_var, get_metadata_dir, get_fulltext_dir

from common import DEFAULT_OUTPUT_DIRECTORY

MODE_ALL = "all"
MODE_RETRIEVE = "retrieve"
MODE_GENERATE_CMDI = "generate-cmdi"
MODE_AGGREGATE_XML = "aggregate-from-xml"

modes = [MODE_ALL, MODE_RETRIEVE, MODE_GENERATE_CMDI, MODE_AGGREGATE_XML]

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    logger.debug(f"sys.argv={sys.argv}")
    if len(sys.argv) <= 1:
        print_usage()
        exit(0)

    if sys.argv[1] not in modes:
        print(f"ERROR: command not recognised: '{sys.argv[1]}'")
        print_usage()
        exit(1)

    run_command(MODE_AGGREGATE_XML, sys.argv)


def run_command(command, arguments):
    logger.info(f"Command: {command}")
    logger.info(f"Arguments: {arguments}")

    output_dir = get_optional_env_var('OUTPUT_DIR', DEFAULT_OUTPUT_DIRECTORY)

    if command == MODE_AGGREGATE_XML:
        if len(arguments) < 4:
            print("ERROR: Provide locations for metadata and fulltext and a resource base URL")
            print_usage()
            exit(1)

        aggregate_from_xml.generate(arguments[0], arguments[1], arguments[2], arguments[3], arguments[4])
    if command == MODE_RETRIEVE:  # retrieve
        if len(arguments) < 1:
            print("ERROR: Provide a set identifier as the first argument")
            print_usage()
            exit(1)
        collection_id = arguments[0]
        api_retrieval.retrieve(collection_id, output_dir)
    if command == MODE_GENERATE_CMDI:  # generate CMDI
        if len(arguments) < 2:
            print("ERROR: Provide locations for metadata and fulltext")
            print_usage()
            exit(1)
        generate_cmdi.generate(arguments[0], arguments[1])


def process_all(ids, output_dir):
    for collection_id in ids:
        api_retrieval.retrieve(collection_id, output_dir)
        generate_cmdi.generate(get_metadata_dir(output_dir, collection_id),
                               get_fulltext_dir(output_dir, collection_id),
                               f"{output_dir}/map-{collection_id}.json")


def print_usage():
    print(f"""
    Usage:
        {sys.executable} {__file__} <collection id> <metadata path> <fulltext path>
                                    <fulltext base URL> <output directory>

    """)


if __name__ == "__main__":
    main()
