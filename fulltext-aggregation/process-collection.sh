#!/bin/bash

set -e

RESOURCES_BASE_URL="https://alpha-vlo.clarin.eu/data/test/resources/"
INPUT_DATA_BASE_DIR="${HOME}/europeana-fulltext-aggregation/resources"
OUTPUT_BASE_DIR="${HOME}/europeana-fulltext-aggregation/output"
DOWNLOAD_DIR="${INPUT_DATA_BASE_DIR}/download"



main() {
  SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
  START_DIR="$(pwd)"

  COLLECTION_ID="$1"
  if ! [ "${COLLECTION_ID}" ]; then
    echo "Usage: $0 <collection id>"
    exit 1
  fi

  METADATA_TARGET_DIR="${INPUT_DATA_BASE_DIR}/${COLLECTION_ID}/metadata"
  FULLTEXT_TARGET_DIR="${INPUT_DATA_BASE_DIR}/${COLLECTION_ID}/fulltext"
  METADATA_DUMP_URL="ftp://download.europeana.eu/newspapers/metadata/${COLLECTION_ID}.zip"
  FULLTEXT_DUMP_URL="ftp://download.europeana.eu/newspapers/fulltext/edm_issue/${COLLECTION_ID}.zip"
  METADATA_DUMP_FILE="${DOWNLOAD_DIR}/${COLLECTION_ID}_metadata.zip"
  FULLTEXT_DUMP_FILE="${DOWNLOAD_DIR}/${COLLECTION_ID}_fulltext.zip"
  COLLECTION_RESOURCES_BASE_URL="${RESOURCES_BASE_URL}${COLLECTION_ID}/fulltext/"

  OUTPUT_DIR="${OUTPUT_BASE_DIR}/${COLLECTION_ID}"

  mkdir -p "${DOWNLOAD_DIR}" "${METADATA_TARGET_DIR}" "${FULLTEXT_TARGET_DIR}" "${OUTPUT_DIR}"
  chmod -R og+rw "${DOWNLOAD_DIR}" "${OUTPUT_DIR}"

  echo "$(date) - Starting metadata download from ${METADATA_DUMP_URL} to ${METADATA_DUMP_FILE}"
  RESULT=1
  while [ "${RESULT}" != "0" ]; do
    download_and_unpack "${METADATA_DUMP_URL}" "${METADATA_DUMP_FILE}" "${METADATA_TARGET_DIR}" "${METADATA_DUMP_URL}.md5sum"
    RESULT=$?
  done

  echo "$(date) - Starting fulltext download from ${FULLTEXT_DUMP_URL} to ${FULLTEXT_DUMP_FILE}"
  RESULT=1
  while [ "${RESULT}" != "0" ]; do
    download_and_unpack "${FULLTEXT_DUMP_URL}" "${FULLTEXT_DUMP_FILE}" "${FULLTEXT_TARGET_DIR}" "${FULLTEXT_DUMP_URL}.md5sum"
    RESULT=$?
    if [ "${RESULT}" != "0" ]; then
      echo "$(date) - Retrying"
    fi
  done

  echo "$(date) - Running aggregation scripts."
  cd "${SCRIPT_DIR}" && bash run.sh 'aggregate-from-xml' \
    "${METADATA_TARGET_DIR}"\
    "${FULLTEXT_TARGET_DIR}"\
    "${COLLECTION_RESOURCES_BASE_URL}" \
    "${OUTPUT_DIR}"

  cd "${START_DIR}"
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
      if ! echo "$(cat "${MD5_FILE}") ${FILE}" | md5sum -c; then
        echo "$(date) - ERROR: checksum check failed"
        rm "${FILE}"
        return 1
      else
        rm "${MD5_FILE}"
      fi
    fi

    echo "$(date) - Decompressing ${FILE} in ${DIR}"
    cd "${DIR}"
    if 7z-docker x "${FILE}"; then
      # Move all files in target directory 'root'
      find "${DIR}" -mindepth 2 -type f -exec "${MV_COMMAND:-mv}" -t "${DIR}" -i '{}' +
      return 0
    fi
  fi

  # signal to retry (or give up)
  return 1
}

7z-docker() {
  COMMAND="$1"
  ZIP_FILE="$(realpath -- "$2")"
  ZIP_DIR="$(dirname -- "${ZIP_FILE}")"
  ZIP_NAME="$(basename -- "${ZIP_FILE}")"

  docker run --rm -it -u "${UID}" \
    --workdir '/data' -v "$(pwd):/data" -v "${ZIP_DIR}:/input" \
    crazymax/7zip:16.02 7za "${COMMAND}" "/input/${ZIP_NAME}"
}

main "$@"

