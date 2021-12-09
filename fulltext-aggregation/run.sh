#!/bin/bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

MODE="$1"
MD_PATH="$2"
FT_PATH="$3"
BASE_URL="$4"
OUTPUT_DIR="$5"

echo "$(date) - run.sh - Mode: '${MODE}'"
echo "$(date) - run.sh - Metadata directory: '${MD_PATH}'"
echo "$(date) - run.sh - Full text directory: '${FT_PATH}'"
echo "$(date) - run.sh - Output directory: '${OUTPUT_DIR}'"
echo "$(date) - run.sh - Resources base URL: '${BASE_URL}'"

( cd "${SCRIPT_DIR}" && docker-compose run \
  -v "${MD_PATH}:/input/metadata" \
  -v "${FT_PATH}:/input/fulltext" \
  -e "OUTPUT_DIR=${OUTPUT_DIR}"
  'europeana-aggregator' "${MODE}" '/input/metadata' '/input/fulltext' "${BASE_URL}" '/output' )
