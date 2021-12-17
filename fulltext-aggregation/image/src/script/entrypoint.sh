#!/bin/bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
START_DIR="$(pwd)"

usage() {
  echo "
  Usage: ${0} <command> <arguments..>

  Commands:
    process
  "
}

main() {
  COMMAND="$1"
  info "Command: ${COMMAND}"
  shift
  ARGUMENTS="$@"
  info "Arguments:" "$@"

  case "${COMMAND}" in

    'process')
      "${SCRIPT_DIR}/process-collection.sh" "${COLLECTION_ID}"
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
