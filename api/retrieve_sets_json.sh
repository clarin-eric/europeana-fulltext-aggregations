#!/usr/bin/env bash
source env.sh
curl -L "https://www.europeana.eu/api/v2/search.json?wskey=${KEY}&query=europeana_collectionName:*&facet=europeana_collectionName&f.europeana_collectionName.facet.limit=4000&profile=facets&rows=0"

