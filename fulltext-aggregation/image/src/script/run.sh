#!/bin/bash
set -e

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PYTHON_DIR="$(dirname -- "${SCRIPT_DIR}"/..)"

echo "$(date) - run.sh - Collection: '${COLLECTION_ID:?Error - metadata directory argument is not provided!}'"
echo "$(date) - run.sh - Metadata directory: '${METADATA_PATH:?Error - metadata directory argument is not provided!}'"
echo "$(date) - run.sh - Full text directory: '${FULLTEXT_PATH:?Error - full text directory argument is not provided!}'"
echo "$(date) - run.sh - Output directory: '${OUTPUT_DIR:?Error - output directory argument is not provided!}'"
echo "$(date) - run.sh - Resources base URL: '${BASE_URL:?Error - base url argument is not provided!}'"


(
  cd "${PYTHON_DIR}"
  python3 -m __main__.py "$COLLECTION_ID" "$METADATA_PATH" "$FULLTEXT_PATH" "$BASE_URL" "$OUTPUT_DIR"
)

#
#( cd "${SCRIPT_DIR}" \
#  && LOCAL_OUTPUT_DIR=${OUTPUT_DIR} \
#    docker-compose run --rm \
#    -v "${MD_PATH}:/input/metadata" \
#    -v "${FT_PATH}:/input/fulltext" \
#    -e "OUTPUT_DIR=/output" \
#    'europeana-aggregator' "${COLLECTION}" '/input/metadata' '/input/fulltext' "${BASE_URL}" '/output' )
