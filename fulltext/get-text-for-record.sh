#!/usr/bin/env bash
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

if [ -e "${BASE_DIR}/env.sh" ]; then
        source ${BASE_DIR}/env.sh
else
        echo "WARNING: No env.sh file found"
fi

if ! [ "${API_URL}" ]; then
        echo "ERROR: Environment variables API_KEY and/or API_URL not set. Please export these or create an env.sh file that sets these."
        exit 1
fi



print_usage() {
        echo "usage: $0 --collection <collectionId> --record <recordId>"
}

get_anno_pages() {
	COLLECTION="$1" # e.g. 9200338
	RECORD="$2" # e.g. BibliographicResource_3000117673618

	MANIFEST_URL="${API_URL}/presentation/${COLLECTION}/${RECORD}/manifest"
	
	if ! curl -sL "$MANIFEST_URL" | jq -r '.sequences[]|.canvases[]|.otherContent[]|."@id"'
	then
		echo "Failed to retrieve manifest"
		exit 1
	fi
}

fetch_text() {
	COLLECTION="$1" # e.g. 9200338
	RECORD="$2" # e.g. BibliographicResource_3000117673618
	
	get_anno_pages $COLLECTION $RECORD | while read ANNOPAGE; do
			echo Anno page "$ANNOPAGE"
		done
}

main() {
		COLLECTION=""
		RECORD=""
		
	    while [[ $# -gt 0 ]] && [[ ."$1" = .--* ]] ;
        do
                arg="$1"
                shift
                case "$arg" in
                        "--help" )
                                print_usage
                                exit 0
                                ;;
                        "--collection" )        COLLECTION="$1"; shift;;
                        "--record" )            RECORD="$1"; shift;;
                esac
        done

        if ! [ "${COLLECTION}" ] || ! [ "${RECORD}" ]; then
                print_usage
                exit 1
        fi

        fetch_text $COLLECTION $RECORD
}

main $@