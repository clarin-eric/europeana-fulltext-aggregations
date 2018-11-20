#COLLECTION_ID="05815_L_RO_Folkmedia"
COLLECTION_ID=`echo $@|sed -e 's/ /%20/g'`
KEY="DoLz47agJ"
URL="https://www.europeana.eu/api/v2/search.json?wskey=${KEY}&query=europeana_collectionName:${COLLECTION_ID}&rows=1&profile=minimal"
curl -s "$URL" | jq .totalResults
