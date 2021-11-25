import api_retrieval
import sys

MODE_RETRIEVE = "retrieve"
MODE_GENERATE_CMDI = "generate-cmdi"

modes = [MODE_RETRIEVE, MODE_GENERATE_CMDI]


def main():
    if len(sys.argv) <= 1:
        print_usage()
        exit(0)

    if sys.argv[1] not in modes:
        print(f"ERROR: command not recognised: '{sys.argv[1]}'")
        print_usage()
        exit(1)

    run_command(sys.argv[1])


def run_command(command):
    if command == MODE_RETRIEVE: # retrieve
        if len(sys.argv) <= 2:
            print("ERROR: Provide a set identifier as the first argument")
            print_usage()
            exit(1)

        collection_id = sys.argv[2]
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
