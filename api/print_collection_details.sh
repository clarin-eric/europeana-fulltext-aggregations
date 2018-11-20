#!/usr/bin/env bash
while read s; do echo -e "$s\t$(sh ./get_collection_details.sh $s)"; done