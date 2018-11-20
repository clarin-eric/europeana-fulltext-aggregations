#!/usr/bin/env bash
SETS_FILE="sets.txt"
SETS_DETAILS_FILE="sets_details.txt"

echo -e "--------\nRetrieving set IDs\n--------"
bash ./retrieve_set_ids.sh | sort > ${SETS_FILE}
echo -e "--------\nRetrieving set details\n--------"
bash ./print_collection_details.sh < ${SETS_FILE} > ${SETS_DETAILS_FILE}
echo -e "--------\nDone!\n--------"
