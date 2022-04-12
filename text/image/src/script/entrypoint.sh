#!/bin/bash
set -e

COLLECTION_ID="$1"
DEBUG="${DEBUG:-false}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"
DUMP_FTP_BASE_URL="${DUMP_FTP_BASE_URL:-ftp://download.europeana.eu/newspapers/fulltext/edm_issue}"

cd /app/src

python3 '__main__.py' "${COLLECTION_ID}" "${OUTPUT_DIR}"

main "$@"
