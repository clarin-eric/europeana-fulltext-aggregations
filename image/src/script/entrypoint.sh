#!/bin/bash
set -e

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
START_DIR="$(pwd)"

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

  if [ "${RETRIEVE}" = 1 ]; then
      "${SCRIPT_DIR}/retrieve.sh" "${COLLECTION_ID}"
  fi

  if [ "${AGGREGATE}" = 1 ]; then
      INPUT="${INPUT_DIR}/${COLLECTION_ID}"
      OUTPUT="${OUTPUT_DIR}/${COLLECTION_ID}"

      if ! [ -d "${INPUT}" ]; then
        echo "ERROR - Input directory does not exist. Run $0 retrieve first!"
        exit 1
      fi

      mkdir -p "${OUTPUT}"
      (
        cd "${SCRIPT_DIR}/.." \
          && python3 '__main__.py' "${COLLECTION_ID}" "${INPUT}" "${OUTPUT}"
      )
  fi

  if [ "${CLEAN}" = 1 ]; then
    echo "Erasing content for ${COLLECTION_ID} in ${INPUT_DIR}"
    if [ -d "${INPUT_DIR}" ]; then
      ( cd "${INPUT_DIR}" && find . -name "${COLLECTION_ID}" -type d -maxdepth 1 -mindepth 1|xargs rm -rf )
    else
      echo "Error: ${INPUT_DIR} not found"
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
