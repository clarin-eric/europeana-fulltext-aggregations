#!/bin/bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
#<metadata path> <fulltext path> <fulltext base URL> <output directory>
MODE="$1"
MD_PATH="$2"
FT_PATH="$3"
BASE_URL="$4"
OUTPUT_DIR="$5"

( cd "${SCRIPT_DIR}" && docker-compose run \
  -v "${MD_PATH}:/input/metadata" \
  -v "${FT_PATH}:/input/fulltext" \
  -v "${OUTPUT_DIR}:/output" \
  'europeana-aggregator' "${MODE}" '/input/metadata' '/input/fulltext' "${BASE_URL}" '/output' )

