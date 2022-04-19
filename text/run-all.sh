#!/bin/bash
set -e

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
(
	cd "${SCRIPT_DIR}"
	if [ -e '.env' ]; then
	  bash build.sh \
		&& bash run.sh 9200300 \
		&& bash run.sh 9200301 \
		&& bash run.sh 9200303 \
		&& bash run.sh 9200338 \
		&& bash run.sh 9200339 \
		&& bash run.sh 9200356 \
		&& bash run.sh 9200357 \
		&& bash run.sh 9200359 \
		&& bash run.sh 9200396
	else
		echo "Failure: .env file not found. Please copy .env-template to .env before running!"
		exit 1
	fi
)
