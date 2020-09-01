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
TEXT=0
FULLTEXT=0
SOUND=0

print_usage() {
	echo "usage: $0 --collection <collectionId> [--open] [--media] [--text] [--sound] [--fulltext]"
}

query_api() {
	CURSOR="$1"
	REQ_OPTS=(--data-urlencode "wskey=${API_KEY}")
	REQ_OPTS+=(--data-urlencode "profile=minimal")
	REQ_OPTS+=(--data-urlencode "query=europeana_collectionName:${COLLECTION}")
	REQ_OPTS+=(--data-urlencode "rows=500")
	if [ "${OPEN}" -eq 1 ]; then
		REQ_OPTS+=(--data-urlencode "reusability=open")
	fi
	if [ "${MEDIA}" -eq 1 ]; then
		REQ_OPTS+=(--data-urlencode "media=true")
	fi
	if [ "${TEXT}" -eq 1 ]; then
		REQ_OPTS+=(--data-urlencode "qf=TYPE:TEXT")
	fi
	if [ "${SOUND}" -eq 1 ]; then
		REQ_OPTS+=(--data-urlencode "qf=TYPE:SOUND")
	fi
	if [ "${FULLTEXT}" -eq 1 ]; then
		REQ_OPTS+=(--data-urlencode "qf=TEXT_FULLTEXT:true")
	fi
	if [ "${CURSOR}" ] && [ "${CURSOR}" != null ]; then
		REQ_OPTS+=(--data-urlencode "cursor=${CURSOR}")
	fi
	echo curl -GL "${REQ_OPTS[@]}" "${API_URL}" >&2
	curl -GL "${REQ_OPTS[@]}" "${API_URL}" 
}

fetch_ids() {
	#make and process request
	TMP_FILE=$(mktemp)

	NEXT_CURSOR=\*
	while [ "${NEXT_CURSOR}" != null ]; do
		echo "Next cursor ${NEXT_CURSOR}" >&2
		#construct request URL
		if ! query_api "$NEXT_CURSOR" > $TMP_FILE; then
			echo "Error while calling Europeana API"
			exit 1
		fi
		
		jq -r '.items|.[]|.id' < $TMP_FILE

		NEXT_CURSOR=$(jq -r ' .nextCursor' < $TMP_FILE)

		cat $TMP_FILE >&2
	done
	#remove temp response
	rm $TMP_FILE
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
			"--text" ) 		TEXT=1 ;;
			"--sound" ) 		SOUND=1 ;;
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
