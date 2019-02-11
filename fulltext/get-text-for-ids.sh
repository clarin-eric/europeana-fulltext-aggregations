#!/usr/bin/env bash
#
# Script to get full text for the records in a Europeana search API result document
#
# Author: Twan Goosen <twan@clarin.eu>

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
OUTPUT_DIR="${BASE_DIR}/out"

get_text_for_record_id() {
	ID="$1"
	COLLECTION=$(echo "$ID" | sed "s_/\([^/]*\)/.*_\\1_g")
	RECORD=$(echo "$ID" | sed "s_/[^/]*/\(.*\)_\\1_g")
	
	if ! [ "${COLLECTION}" ] || ! [ "${RECORD}" ]; then
		echo "Skipping '$1'" > /dev/stderr
	fi
	
	echo "Collection ${COLLECTION} record ${RECORD}" > /dev/stderr
	${BASE_DIR}/get-text-for-record.sh \
		--collection "${COLLECTION}" \
		--record "${RECORD}"
}

main() {
	if [ "$1" ]; then
		OUTPUT_DIR="$1"
	fi
	
	echo "Writing to $OUTPUT_DIR" > /dev/stderr
	while read RECORD_ID; do
		get_text_for_record_id $RECORD_ID
	done
}

main $@
