#!/bin/bash

RESOURCES_BASE_URL="https://alpha-vlo.clarin.eu/data/europeana-aggregation/"
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
  FULLTEXT_DUMP_FILE="${DOWNLOAD_DIR}/${COLLECTION_ID}_metadata.zip"
  COLLECTION_RESOURCES_BASE_URL="${RESOURCES_BASE_URL}${COLLECTION_ID}/fulltext/"
  OUTPUT_DIR="${OUTPUT_BASE_DIR}/${COLLECTION_ID}"

  mkdir -p "${DOWNLOAD_DIR}" "${METADATA_TARGET_DIR}" "${FULLTEXT_TARGET_DIR}" "${OUTPUT_BASE_DIR}"
  chown -R og+rw "${DOWNLOAD_DIR}" "${OUTPUT_BASE_DIR}"

  echo "$(date) Starting metadata download"
  wget -O "${METADATA_DUMP_FILE}" "${METADATA_DUMP_URL}"
  cd "${METADATA_TARGET_DIR}"
  unzip  "${METADATA_DUMP_FILE}" &
  MD_PID=$!

  echo "$(date) Starting fulltext download"
  wget -O "${FULLTEXT_DUMP_FILE}" "${FULLTEXT_DUMP_URL}"
  cd "${FULLTEXT_TARGET_DIR}"
  unzip  "${FULLTEXT_DUMP_FILE}"

  wait "${MD_PID}"

  cd "${SCRIPT_DIR}" && bash run.sh \
    "${METADATA_TARGET_DIR}"\
    "${FULLTEXT_TARGET_DIR}"\
    "${COLLECTION_RESOURCES_BASE_URL}" \
    "${OUTPUT_DIR}"

  cd "${START_DIR}"
}

main "$@"

