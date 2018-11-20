#!/usr/bin/env bash
source env.sh
curl -L "${SEARCH_API}?wskey=${KEY}&query=europeana_collectionName:*&facet=europeana_collectionName&f.europeana_collectionName.facet.limit=4000&profile=facets&rows=0"

