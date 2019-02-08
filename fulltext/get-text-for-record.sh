#!/usr/bin/env bash
#
# Script to get full text for a Europeana record via the IIIF API
#
# Author: Twan Goosen <twan@clarin.eu>

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
TMP_DIR="$(mktemp -d)"
OUT_DIR="${BASE_DIR}/out"

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
        echo "usage: $0 --collection <collectionId> --record <recordId> [--outdir <outdir>]"
}

get_anno_pages_from_manifest() {
	if ! jq -r '.sequences[]|.canvases[]|.otherContent[]|."@id"'; then
		fail "Failed to find annotation pages"
	fi
}

get_full_text_resource_from_anno() {
	if ! jq -r '.resources[]|select(.dcType=="Page")|.resource."@id"'; then
		fail "Failed to get full text resource"
	fi
}

get_full_text_content_from_resource() {
	if ! jq -r '.value'; then
		fail "Failed to get full text value"
	fi
}

fetch_text() {
	COLLECTION="$1" # e.g. 9200338
	RECORD="$2" # e.g. BibliographicResource_3000117673618
	
	MANIFEST_URL="${API_URL}/presentation/${COLLECTION}/${RECORD}/manifest"
	
	RECORD_OUT_DIR="${OUT_DIR}/${COLLECTION}/${RECORD}"
	if ! mkdir -p "${RECORD_OUT_DIR}"; then
		fail "Output directory could not be created"
	fi
	
	TMP_OUT=$(make_temp_file manifest)
	echo "Getting manifest for ${COLLECTION}/${RECORD}" > /dev/stderr
	if ! curl -sL "$MANIFEST_URL" > "$TMP_OUT"; then
		fail "Failed to read manifest at ${MANIFEST_URL}"
	else
		PAGE_COUNT=0
		cat "$TMP_OUT" \
			| get_anno_pages_from_manifest \
			| while read ANNOPAGE; do
				# get annotation page document
				TMP_OUT=$(make_temp_file anno)
				echo "...getting annotation page" > /dev/stderr
				if ! curl -sL "$ANNOPAGE" > "$TMP_OUT"; then
					fail "Failed to read annotation page at ${ANNOPAGE}"
				else
					cat "$TMP_OUT" \
						| get_full_text_resource_from_anno
				fi
			done \
			| while read FT_RESOURCE; do
				# get full text resource document
				TMP_OUT=$(make_temp_file ft)
				echo "... ...getting full text resource" > /dev/stderr
				if ! curl -sL "$FT_RESOURCE" > "$TMP_OUT"; then
					fail "Failed to read full text resource page at ${FT_RESOURCE}"
				else
					# extract full text content and write to file
					OUT_FILE="${RECORD_OUT_DIR}/page$((PAGE_COUNT++)).txt"
					echo "... ... ...writing output to ${OUT_FILE}"
					cat "$TMP_OUT" \
						| get_full_text_content_from_resource > "$OUT_FILE"
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
                        "--outdir" )            OUT_DIR="$1"; shift;;
                esac
        done

        if ! [ "${COLLECTION}" ] || ! [ "${RECORD}" ]; then
                print_usage
                exit 1
        fi

        fetch_text $COLLECTION $RECORD
        clean_up_tmp
}

# Utils

clean_up_tmp() {
	if [ -d "${TMP_DIR}" ]; then
		rm -rf "${TMP_DIR}"
	fi
}

make_temp_file() {
	mkdir -p  "${TMP_DIR}"
	TMP_FILE_NAME="${TMP_DIR}/$1-$(date +%Y%m%d%H%M%S)"
	if ! [ -e "${TMP_FILE_NAME}" ] && touch "${TMP_FILE_NAME}";
		then echo "${TMP_FILE_NAME}"
	else
		echo "Could not make temp file. Trying mktemp" > /dev/stderr
		mktemp
	fi
}

fail() {
	echo "ERROR: $@" > /dev/stderr
	clean_up_tmp
	exit 1
}

# Run main

main $@