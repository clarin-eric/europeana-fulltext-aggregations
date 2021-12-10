import aggregate_from_xml
import logging
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    if len(sys.argv) < 5:
        print("ERROR: Provide locations for metadata and fulltext and a resource base URL")
        print_usage()
        exit(1)

    arguments = sys.argv[1:]
    logger.info(f"Arguments: {arguments}")
    aggregate_from_xml.generate(arguments[0], arguments[1], arguments[2], arguments[3], arguments[4])


def print_usage():
    print(f"""
    Usage:
        {sys.executable} {__file__} <collection id> <metadata path> <fulltext path>
                                    <fulltext base URL> <output directory>

    """)


if __name__ == "__main__":
    main()
