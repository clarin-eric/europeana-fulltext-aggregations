#!/usr/bin/env bash
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
COLLECTION=""

print_usage() {
	echo "usage: $0 --collection <collectionId> [--open] [--media] [--fulltext]"
}

harvest() {
	set -e
	OUT_DIR=${BASE_DIR}/out/${COLLECTION}
	mkdir -p $OUT_DIR

	echo "Output to ${OUT_DIR}"

	echo "Collecting IDs from API"
	${BASE_DIR}/get-filtered-record-ids.sh $@ 2>/dev/null | ${BASE_DIR}/ids2xml.sh > ${OUT_DIR}/selection.xml
}

main() {
	ARGS=$@

	while [[ $# -gt 0 ]] && [[ ."$1" = .--* ]] ;
	do
		arg="$1"
		shift
		case "$arg" in
			"--help" )
				print_usage
				exit 0
				;;
			"--collection" )	COLLECTION="$1"; shift;;
		esac
	done

	if ! [ "${COLLECTION}" ]; then
		print_usage
		exit 1
	fi

	harvest $ARGS
}

main $@

