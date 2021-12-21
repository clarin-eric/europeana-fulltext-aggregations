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
  ARGUMENTS="$@"
  info "Arguments:" "$@"

  case "${COMMAND}" in

    'retrieve')
      "${SCRIPT_DIR}/retrieve.sh" "${ARGUMENTS}"
      ;;

    'aggregate')
      (cd "${SCRIPT_DIR}" && python3 -m __main.py__ aggregate "${ARGUMENTS}")
      ;;

    'clean')
      echo "Erasing content of ${INPUT_DIR}"
      if [ -d "${INPUT_DIR}" ]; then
        ( cd "${INPUT_DIR}" && find . -type d -maxdepth 1 -mindepth 1|xargs rm -rvf )
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
