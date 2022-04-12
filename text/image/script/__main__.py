import retrieve_and_extract
import logging
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    if len(sys.argv) < 2:
        print("ERROR: Provide collection id and output location")
        print_usage()
        exit(1)

    arguments = sys.argv[1:]
    logger.info(f"Arguments: {arguments}")
    retrieve_and_extract.main(arguments[0], arguments[1])


def print_usage():
    print(f"""
    Usage:
        {sys.executable} {__file__} <collection id> <output dir>

    """)


if __name__ == "__main__":
    main()
