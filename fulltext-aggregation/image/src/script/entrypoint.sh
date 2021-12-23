#!/bin/bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
START_DIR="$(pwd)"

usage() {
  echo "
  Usage: ${0} <command> <arguments..>

  Commands:
    retrieve <collection id>
    aggregate <...>
    clean
  "
}

main() {
  COMMAND="$1"
  info "Command: ${COMMAND}"
  shift
  ARGUMENTS=( "$@" )
  info "Arguments:" "${ARGUMENTS[@]}"

  [ "${INPUT_DIR:?Error - input directory not set}" ]
  [ "${OUTPUT_DIR:?Error - Output directory not set}" ]

  case "${COMMAND}" in

    'retrieve')
      COLLECTION_ID="${ARGUMENTS[0]}"

      if ! [ "${COLLECTION_ID}" ]; then
        echo "ERROR - No collection identifier provided"
        exit 1
      fi

      "${SCRIPT_DIR}/retrieve.sh" "${COLLECTION_ID}"
      ;;

    'aggregate')
      COLLECTION_ID="${ARGUMENTS[0]}"

      if ! [ "${COLLECTION_ID}" ]; then
        echo "ERROR - No collection identifier provided"
        exit 1
      fi

      INPUT="${INPUT_DIR}/${COLLECTION_ID}"
      OUTPUT="${OUTPUT_DIR}/${COLLECTION_ID}"
      mkdir -p "${OUTPUT}"
      (
        cd "${SCRIPT_DIR}/.." \
          && python3 '__main__.py' "${COLLECTION_ID}" "${INPUT}" "${OUTPUT}"
      )
      ;;

    'clean')
      echo "Erasing content of ${INPUT_DIR}"
      if [ -d "${INPUT_DIR}" ]; then
        ( cd "${INPUT_DIR}" && find . -type d -maxdepth 1 -mindepth 1|xargs rm -rf )
      else
        echo "Error: ${INPUT_DIR} not found"
      fi
      ;;

    '*')
      usage
      exit 1
      ;;
  esac
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
