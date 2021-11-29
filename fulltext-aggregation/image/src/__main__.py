import api_retrieval
import logging
import sys

MODE_RETRIEVE = "retrieve"
MODE_GENERATE_CMDI = "generate-cmdi"

modes = [MODE_RETRIEVE, MODE_GENERATE_CMDI]

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

    run_command(sys.argv[1], sys.argv[2:])


def run_command(command, arguments):
    logger.info(f"Command: {command}")
    logger.info(f"Arguments: {arguments}")

    if command == MODE_RETRIEVE: # retrieve
        if len(arguments) < 1:
            print("ERROR: Provide a set identifier as the first argument")
            print_usage()
            exit(1)

        collection_id = arguments[0]
        api_retrieval.retrieve(collection_id)
    if command == MODE_GENERATE_CMDI:  # generate CMDI
        print("Mode not implemented")


def print_usage():
    print(f"""
    Usage:
        {sys.executable} {__file__} <command> <args>

    Commands:
        {MODE_RETRIEVE} <collectionId>
        {MODE_GENERATE_CMDI} <path>  
    """)


if __name__ == "__main__":
    main()
