#!/usr/bin/env bash
source env.sh
COLLECTION_ID=`echo $@|sed -e 's/ /%20/g'`
URL="${SEARCH_API}?wskey=${KEY}&query=europeana_collectionName:${COLLECTION_ID}&rows=1&profile=minimal"
curl -s "$URL" | jq .totalResults
