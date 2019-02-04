#!/usr/bin/env bash
PREFIX="http://data.europeana.eu/item/"

echo '<?xml version="1.0" encoding="UTF-8"?>
<records>'

while read REC_ID; do
  echo -e "\t<record identifier=\"${PREFIX}${REC_ID}\">${REC_ID}</record>"
done

echo '</records>'

