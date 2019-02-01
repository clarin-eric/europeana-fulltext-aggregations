#!/usr/bin/env bash
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

if [ -e "${BASE_DIR}/env.sh" ]; then
	source ${BASE_DIR}/env.sh
else
	echo "WARNING: No env.sh file found"
fi

if ! [ "${API_KEY}" ] || ! [ "${API_URL}" ]; then
	echo "ERROR: Environment variables API_KEY and/or API_URL not set. Please export these or create an env.sh file that sets these."
	exit 1
fi

COLLECTION=""
OPEN=0
MEDIA=0
FULLTEXT=0

print_usage() {
	echo "usage: $0 --collection <collectionId> [--open] [--media] [--fulltext]"
}

make_query_url() {
	BASE_URL="${API_URL}?wskey=${API_KEY}"
	REQ_URL="${BASE_URL}&query=europeana_collectionName:${COLLECTION}&cursor=*&profile=minimal"
	if [ "${OPEN}" -eq 1 ]; then
		REQ_URL="${REQ_URL}&reusability=open"
	fi
	if [ "${MEDIA}" -eq 1 ]; then
		REQ_URL="${REQ_URL}&media=true"
	fi
	if [ "${FULLTEXT}" -eq 1 ]; then
		REQ_URL="${REQ_URL}&qf=TEXT_FULLTEXT:true"
	fi
	echo "$REQ_URL"
}

fetch_ids() {
	REQ_URL=$(make_query_url)
	echo "Request URL: $REQ_URL"
	#TODO: make and process request
}


main() {
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
			"--open" ) 		OPEN=1 ;;
			"--media" ) 		MEDIA=1 ;;
			"--fulltext" ) 		FULLTEXT=1 ;;
		esac
	done

	if ! [ "${COLLECTION}" ]; then
		print_usage
		exit 1
	fi

	fetch_ids $COLLECTION $OPEN $MEDIA $FULLTEXT
}

main $@
