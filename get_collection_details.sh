#!/usr/bin/env bash
source env.sh
COLLECTION_ID=`echo $@|sed -e 's/ /%20/g'|sed -e 's/!/%21/g'|sed -e 's/?/%3F/g'|sed -e 's/:/%3A/g'`
URL="${SEARCH_API}?wskey=${KEY}&query=europeana_collectionName:%22${COLLECTION_ID}%22&rows=0&profile=facets&facet=TYPE&facet=MIME_TYPE&facet=LANGUAGE&facet=TEXT_FULLTEXT"

RESULT="$(curl -s $URL)"
COUNT=`jq .totalResults <(echo $RESULT)`
TYPES=`jq '.facets? | .[] | select(.name=="TYPE") | .fields|.[].label'  <(echo $RESULT)|tr '\n' ';'`
MIME_TYPES=`jq '.facets? | .[] | select(.name=="MIME_TYPE") | .fields|.[].label'  <(echo $RESULT)|tr '\n' ';'`
LANGUAGES=`jq '.facets? | .[] | select(.name=="LANGUAGE") | .fields|.[].label'  <(echo $RESULT)|tr '\n' ';'`
FULLTEXT=`jq '.facets? | .[] | select(.name=="TEXT_FULLTEXT") | .fields|.[].label'  <(echo $RESULT)|tr '\n' ';'`

echo -e "$COUNT\t$TYPES\t$FULLTEXT\t$LANGUAGES\t$MIME_TYPES"
