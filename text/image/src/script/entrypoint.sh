#!/bin/bash
set -e

COLLECTION_ID="$1"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"

main() {
  if ! [ "${COLLECTION_ID}" ]; then
    usage; exit 1
  fi

  cd /app
  python3 '__main__.py' "${COLLECTION_ID}" "${OUTPUT_DIR}"
}

usage() {
  echo "
  Usage: ${0} <collection id>
  "
}

main "$@"
