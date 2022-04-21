#!/bin/bash
set -e

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

usage() {
  echo "
  Usage: ${0} <commands..> <collection id>

  Commands:
    retrieve|aggregate|clean
  "
}

main() {
  # check required environment variables
  [ "${INPUT_DIR:?Error - input directory not set}" ]
  [ "${OUTPUT_DIR:?Error - Output directory not set}" ]

  if [ "$#" -lt 2 ]; then
    usage
    exit 1
  fi

  RETRIEVE=0
  AGGREGATE=0
  CLEAN=0

  while [ "$#" -gt 1 ]; do
    case "$1" in
      'retrieve')
        RETRIEVE=1 ;;
      'aggregate')
        AGGREGATE=1 ;;
      'clean')
        CLEAN=1 ;;
      '*')
        usage; exit 1 ;;
    esac
    shift
  done

  if [ $((RETRIEVE+AGGREGATE+CLEAN)) = 0 ]; then
    usage
    exit 1
  fi

  COLLECTION_ID="$1"

  echo "Retrieve: ${RETRIEVE}"
  echo "Aggregate: ${AGGREGATE}"
  echo "Clean: ${CLEAN}"
  echo "Collection ID: ${COLLECTION_ID}"

  if ! [ "${COLLECTION_ID}" ]; then
    echo "ERROR - No collection identifier provided"
    exit 1
  fi
  
  # retrieve input data
  if [ "${RETRIEVE}" = 1 ]; then
      "${SCRIPT_DIR}/retrieve.sh" "${COLLECTION_ID}"
  fi

  # process (aggregate) input data to create new data
  if [ "${AGGREGATE}" = 1 ]; then
      if ! [ "${TEMP_OUTPUT_DIR}" ]; then
        TEMP_OUTPUT_DIR="${OUTPUT_DIR}/../temp"
        if ! [ -d "${TEMP_OUTPUT_DIR}" ] && ! mkdir -p "${TEMP_OUTPUT_DIR}"; then
          echo "Error: could not make temporary output dir at ${TEMP_OUTPUT_DIR}"
          exit 1
        fi
      fi

      INPUT="${INPUT_DIR}/${COLLECTION_ID}"
      OUTPUT="${OUTPUT_DIR}/${COLLECTION_ID}"
      NEW_OUTPUT="${TEMP_OUTPUT_DIR}/${COLLECTION_ID}"
      export COLLECTION_ID INPUT OUTPUT NEW_OUTPUT
      if bash "${SCRIPT_DIR}/aggregate.sh"; then
        echo "Done. Archiving results..."
        # zip output (TODO: make optional?)
        ZIP_TARGET="${OUTPUT_DIR}/${COLLECTION_ID}.zip"
        if [ -e "${ZIP_TARGET}" ]; then
          rm "${ZIP_TARGET}"
        fi
        zip -jrq "${ZIP_TARGET}" "${OUTPUT}"
        echo "Results archived in ${ZIP_TARGET}"
      else
        echo "Aggregation failed"
        exit 1
      fi
  fi
  
  # clean input data and other unused content
  if [ "${CLEAN}" = 1 ]; then
    echo "Erasing content for ${COLLECTION_ID} in ${INPUT_DIR}"
    if [ -d "${INPUT_DIR}" ]; then
      ( cd "${INPUT_DIR}" && find . -name "${COLLECTION_ID}" -type d -maxdepth 1 -mindepth 1 -print0|xargs -0 rm -rf )
    else
      echo "Error: ${INPUT_DIR} not found"
    fi
    
    OUTPUT_TMP="${TEMP_OUTPUT_DIR}/${COLLECTION_ID}"
    if [ -d "${OUTPUT_TMP}" ]; then
      	echo "Cleaning up temporary output at ${OUTPUT_TMP}"
      	rm -rf "${OUTPUT_TMP}"
    fi
  fi
}

log() {
  LEVEL="$1"
  shift
  echo "[$(date) - $(basename "$0") - ${LEVEL}]" "$@"
}

info() {
  log "INFO" "$@"
}

error() {
  log "ERROR" "$@"
}

main "$@"
