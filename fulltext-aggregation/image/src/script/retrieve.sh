#!/bin/bash

set -e

RESOURCES_BASE_URL="${RESOURCES_BASE_URL:-https://alpha-vlo.clarin.eu/data/test/resources/}"
INPUT_DATA_BASE_DIR="${INPUT_DIR}"
OUTPUT_BASE_DIR="${OUTPUT_DIR}"
DOWNLOAD_DIR="${INPUT_DATA_BASE_DIR}/download"


main() {
  SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
  START_DIR="$(pwd)"

  COLLECTION_ID="${1}"

  if ! [ "${COLLECTION_ID}" ]; then
    echo "Error: COLLECTION_ID not set"
    exit 1
  fi

  METADATA_TARGET_DIR="${INPUT_DATA_BASE_DIR}/${COLLECTION_ID}"
  METADATA_DUMP_URL="ftp://download.europeana.eu/dataset/XML/${COLLECTION_ID}.zip"
  METADATA_DUMP_FILE="${DOWNLOAD_DIR}/${COLLECTION_ID}_metadata.zip"

  OUTPUT_DIR="${OUTPUT_BASE_DIR}/${COLLECTION_ID}"

  mkdir -p "${DOWNLOAD_DIR}" "${METADATA_TARGET_DIR}" "${OUTPUT_DIR}"
  chmod -R og+rw "${DOWNLOAD_DIR}" "${OUTPUT_DIR}"

  echo "$(date) - Starting metadata download from ${METADATA_DUMP_URL} to ${METADATA_DUMP_FILE}"
  RESULT=1
  while [ "${RESULT}" != "0" ]; do
    download_and_unpack "${METADATA_DUMP_URL}" "${METADATA_DUMP_FILE}" "${METADATA_TARGET_DIR}" "${METADATA_DUMP_URL}.md5sum"
    RESULT=$?
  done

  echo "$(date) - Done retrieving and unpacking for collection ${COLLECTION_ID}."
}

download_and_unpack() {
  URL="$1"
  FILE="$2"
  DIR="$3"
  CHECKSUM_URL="$4"
  if wget -O "${FILE}" "${URL}"; then
    if [ "${CHECKSUM_URL}" ]; then
      echo "$(date) - Checking file integrity (${CHECKSUM_URL})"
      MD5_FILE="$(mktemp)"
      wget -q -O "${MD5_FILE}" "${CHECKSUM_URL}"
      if ! echo "$(cat "${MD5_FILE}")  ${FILE}" | md5sum -c; then
        echo "$(date) - ERROR: checksum check failed"
        rm "${FILE}"
        return 1
      else
        rm "${MD5_FILE}"
      fi
    fi

    echo "$(date) - Decompressing ${FILE} in ${DIR}"
    cd "${DIR}"
    if 7z x "${FILE}"; then
      # Move all files in target directory 'root'
      find "${DIR}" -mindepth 2 -type f -exec "${MV_COMMAND:-mv}" -t "${DIR}" -i '{}' +
      return 0
    fi
  fi

  # signal to retry (or give up)
  return 1
}

main "$@"

