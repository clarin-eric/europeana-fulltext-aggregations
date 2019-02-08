#!/usr/bin/env bash
#
# Script to get full text for a Europeana record via the IIIF API
#
# Author: Twan Goosen <twan@clarin.eu>

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

TMP_FILES=()


print_usage() {
        echo "usage: $0 --collection <collectionId> --record <recordId>"
}

clean_up_tmp() {
	for f in "${TMP_FILES[@]}"; do
		if [ -e "$f" ]; then
			rm "$f"
		fi
	done
}

fail() {
	echo "ERROR: $@"
	clean_up_tmp
	exit 1
}

get_anno_pages_from_manifest() {
	if ! jq -r '.sequences[]|.canvases[]|.otherContent[]|."@id"'; then
		fail "Failed to find annotation pages"
	fi
}

get_full_text_resource_from_anno() {
	if ! jq -r '.resources[]|select(.dcType=="Page")|.resource."@id"'; then
		fail "Failed to full text resource"
	fi
}

fetch_text() {
	COLLECTION="$1" # e.g. 9200338
	RECORD="$2" # e.g. BibliographicResource_3000117673618
	
	MANIFEST_URL="${API_URL}/presentation/${COLLECTION}/${RECORD}/manifest"
	
	TMP_MANIFEST_OUT=$(mktemp)
	TMP_FILES+=($TMP_MANIFEST_OUT)
	echo "Getting manifest for ${COLLECTION}/${RECORD}" > /dev/stderr
	if ! curl -sL "$MANIFEST_URL" > "$TMP_MANIFEST_OUT"; then
		fail "Failed to read manifest at ${MANIFEST_URL}"
	else
		cat "$TMP_MANIFEST_OUT" \
			| get_anno_pages_from_manifest \
			| while read ANNOPAGE; do
				TMP_ANNO_OUT=$(mktemp)
				TMP_FILES+=($TMP_ANNO_OUT)
				echo "...Getting annotation page" > /dev/stderr
				if ! curl -sL "$ANNOPAGE" > "$TMP_ANNO_OUT"; then
					fail "Failed to read annotation page at ${ANNOPAGE}"
				else
					cat "$TMP_ANNO_OUT" \
						| get_full_text_resource_from_anno
				fi
			done
	fi
	
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
        clean_up_tmp
}

main $@