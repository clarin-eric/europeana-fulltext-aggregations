import aggregate_collection
import logging
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    if len(sys.argv) < 3:
        print("ERROR: Provide collection id and locations for input and output")
        print_usage()
        exit(1)

    arguments = sys.argv[1:]
    logger.info(f"Arguments: {arguments}")
    aggregate_collection.aggregate(arguments[0], arguments[1], arguments[2])


def print_usage():
    print(f"""
    Usage:
        {sys.executable} {__file__} <collection id> <metadata path> <output directory>

    """)


if __name__ == "__main__":
    main()
