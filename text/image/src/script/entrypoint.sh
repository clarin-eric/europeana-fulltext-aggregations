#!/bin/bash
set -e

DEBUG="${DEBUG:-false}"
DO_CLEAN_UP="${DO_CLEAN_UP:-true}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"
TEMP_DIR="$(mktemp -d)"
FULLTEXT_BASE_URL="${FULLTEXT_BASE_URL:-ftp://download.europeana.eu/newspapers/fulltext/edm_issue}"

SAXON_JAVA_OPTS=("-Djdk.xml.entityExpansionLimit=${JDK_XML_ENTITY_EXPANSION_LIMIT:-60000000}")
WGET_OPTS=()
_7Z_OPTS=()

echo "OUTPUT_DIR: ${OUTPUT_DIR?err}"
echo "FULLTEXT_BASE_URL: ${FULLTEXT_BASE_URL?err}"

if [ "${DEBUG}" = 'true' ]; then
	echo "Debug enabled"
	set -x
	_7Z_OPTS+=(-bb3)
else
	WGET_OPTS+=(-q)
	_7Z_OPTS+=(-bd -bb0 -bt)
fi

if [ "${DO_CLEAN_UP}" != 'true' ]; then
	echo "Warning: cleaning up disabled!"
fi

if ! [ -d "${OUTPUT_DIR}" ]; then
	echo "Error: output dir '${OUTPUT_DIR}' does not exist"
fi

main() {
	for DATA_SET in "$@"; do
		echo "Processing data set ${DATA_SET}"
		ZIP_URL="${FULLTEXT_BASE_URL}/${DATA_SET}.zip"
		ZIP_TARGET="${TEMP_DIR}/${DATA_SET}.zip"
		CONTENT_DIR="${TEMP_DIR}/${DATA_SET}"
		DATA_SET_OUTPUT_DIR="${OUTPUT_DIR}/${DATA_SET}"
		
		mkdir -p "${DATA_SET_OUTPUT_DIR}"

		# retrieve fulltext zip
		echo "Retrieving zip file from ${ZIP_URL}..."
		get_and_check_md5 "${ZIP_TARGET}" "${ZIP_URL}" "${ZIP_URL}.md5sum"
	
		# extract
		echo "Uncompressing..."
		mkdir -p "${CONTENT_DIR}"
		7z x "${_7Z_OPTS[@]}" -y -o"${CONTENT_DIR}" "${ZIP_TARGET}"
		if [ "${DO_CLEAN_UP}" = 'true' ]; then
			echo "Cleaning up zip"
			rm -rf "${ZIP_TARGET}"
		fi
		
		XML_DIR="${CONTENT_DIR}/${DATA_SET}"
		echo "$(find "${XML_DIR}" -maxdepth 1 -type f -name '*.xml'|wc -l) XML files in ${XML_DIR}"
		
		if ! [ -d "${XML_DIR}" ]; then
			echo "Error: XML content directory not found at expected location ${XML_DIR}"
			exit 1
		fi
	
		# transform
		echo "Extracting text to output directory..."
		java "${SAXON_JAVA_OPTS[@]}" -jar "${SAXON_JAR_PATH}" \
			-s:"${XML_DIR}" \
			-o:"${DATA_SET_OUTPUT_DIR}" \
			-xsl:"${EDM2TXT_XSLT_PATH}" \
			-threads:"${SAXON_THREADS:-1}"
	
		# clean up content
		if [ "${DO_CLEAN_UP}" = 'true' ]; then
			echo "Cleaning up uncompressed content"
			rm -rf "${CONTENT_DIR}"
		fi
	done
}

get_and_check_md5() {
	OUT="$1"
	URL="$2"
	MD5_URL="$3"
	
	MD5="$(wget -q -O - ${MD5_URL})"
	wget "${WGET_OPTS[@]}" -O "${OUT}" "${URL}" \
		&& echo "${MD5}  ${OUT}" | md5sum -c
}

main "$@"
