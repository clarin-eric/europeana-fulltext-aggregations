#!/bin/bash
set -e

if ! ([ "${INPUT}" ] && [ "${OUTPUT}" ] && [ "${NEW_OUTPUT}" ] && [ "${COLLECTION_ID}" ]); then
  echo "Error: one or more mandatory variable(s) not set (INPUT, OUTPUT, NEW_OUTPUT, COLLECTION_ID)"
  exit 1
fi


if ! [ -d "${INPUT}" ]; then
  echo "ERROR - Input directory does not exist. Run $0 retrieve first!"
  exit 1
fi

if [ -d "${NEW_OUTPUT}" ]; then
  echo "Cleaning up temporary output at ${NEW_OUTPUT}"
  rm -rf "${NEW_OUTPUT}"
fi

mkdir -p "${NEW_OUTPUT}"
(
  if python3 '__main__.py' "${COLLECTION_ID}" "${INPUT}" "${NEW_OUTPUT}"; then
    # success: move to final output location, replace existing if applicable
    echo "Moving output into place"

    OLD_OUTPUT="${OUTPUT}_old"
    if [ -d "${OUTPUT}" ]; then
      echo "Moving existing output at ${OUTPUT} out of the way"
      mv "${OUTPUT}" "${OLD_OUTPUT}"
    fi
    # Move new output to old location
    if mv "${NEW_OUTPUT}" "${OUTPUT}"; then
      if [ -d "${OLD_OUTPUT}" ]; then
        rm -rf "${OLD_OUTPUT}"
      fi
    fi
  else
    echo "Failed aggregation. Output left in ${NEW_OUTPUT}"
    exit 1
  fi
)
