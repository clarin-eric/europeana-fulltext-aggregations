#!/bin/bash
set -e

COLLECTION_TARGET_DIR="${INPUT_DIR}"
DOWNLOAD_DIR="${COLLECTION_TARGET_DIR}/download"


main() {
  COLLECTION_ID="${1}"

  if ! [ "${COLLECTION_ID}" ]; then
    echo "Error: COLLECTION_ID not set"
    exit 1
  fi

  COLLECTION_TARGET_DIR="${COLLECTION_TARGET_DIR}/${COLLECTION_ID}"
  METADATA_DUMP_URL="ftp://download.europeana.eu/dataset/XML/${COLLECTION_ID}.zip"
  METADATA_DUMP_FILE="${DOWNLOAD_DIR}/${COLLECTION_ID}_metadata.zip"

  mkdir -p "${DOWNLOAD_DIR}"
  chmod -R og+rw "${DOWNLOAD_DIR}"

  echo "$(date) - Starting metadata download from ${METADATA_DUMP_URL} to ${METADATA_DUMP_FILE}"
  RESULT=1
  while [ "${RESULT}" != "0" ]; do
    download_and_unpack "${METADATA_DUMP_URL}" "${METADATA_DUMP_FILE}" "${COLLECTION_TARGET_DIR}" "${METADATA_DUMP_URL}.md5sum"
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
    mkdir -p "${DIR}" && cd "${DIR}"
    if 7z x "${FILE}" -aoa; then
      # Move all files in target directory 'root'
      find "${DIR}" -mindepth 2 -type f -exec "${MV_COMMAND:-mv}" -t "${DIR}" -i '{}' +
      rm "${FILE}"
      return 0
    fi
  fi

  # Clean up download
  if [ -e "${FILE}" ]; then
    rm "${FILE}"
  fi

  # signal to retry (or give up)
  return 1
}

main "$@"

