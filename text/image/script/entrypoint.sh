#!/bin/bash
set -e

DO_CLEAN_UP="${DO_CLEAN_UP:-true}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"
TEMP_DIR="$(mktemp -d)"
FULLTEXT_BASE_URL="${FULLTEXT_BASE_URL:-ftp://download.europeana.eu/newspapers/fulltext/edm_issue}"

if ! [ -d "${OUTPUT_DIR}" ]; then
	echo "Error: output dir '${OUTPUT_DIR}' does not exist"
fi

if [ "${DO_CLEAN_UP}" != 'true' ]; then
	echo "Warning: cleaning up disabled!"
fi

for DATA_SET in "$@"; do
	echo "Processing data set ${DATA_SET}"
	ZIP_URL="${FULLTEXT_BASE_URL}/${DATA_SET}.zip"
	ZIP_TARGET="${TEMP_DIR}/${DATA_SET}.zip"
	CONTENT_DIR="${TEMP_DIR}/${DATA_SET}"	

	# retrieve fulltext zip
	echo "Retrieving zip file from ${ZIP_URL}..."
	wget -q -O "${ZIP_TARGET}" "${ZIP_URL}"
	
	# extract
	echo "Decompressing..."
	mkdir -p "${CONTENT_DIR}"
	unzip -q "${ZIP_TARGET}" -d "${CONTENT_DIR}"
	if [ "${DO_CLEAN_UP}" = 'true' ]; then
		echo "Cleaning up zip"
		rm -rf "${ZIP_TARGET}"
	fi
	
	# transform
	java -jar "${SAXON_JAR_PATH}" -xsl:"${EDM2TXT_XSLT_PATH}" -s:"${CONTENT_DIR}" -o:"${OUTPUT_DIR}"
	
	# clean up content
	if [ "${DO_CLEAN_UP}" = 'true' ]; then
		echo "Cleaning up decompressed content"
		rm -rf "${CONTENT_DIR}"
	fi
done
