#!/usr/bin/env bash
echo -e "ID\tCount\tTypes\tFull text\tLanguages\tMIME types"
while read s; do
	vals="$(bash ./get_collection_details.sh ${s})"
	echo -e "${s}\t${vals}"
done
