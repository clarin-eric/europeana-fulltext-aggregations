# Europeana fulltext resource aggregation
Usage with docker:

```shell
bash build.sh # only before first run or after an update of the sources

cp .env-template .env
vi .env # or editor of choice :)
## configure a local output directory, remote URL for records and other settings

COLLECTION_ID=...... # for instance '9200396'

`# retrieve metadata dump from server` && \
./run.sh retrieve "${COLLECTION_ID}" && \
`# run aggregation scripts` && \ 
./run.sh aggregate "${COLLECTION_ID}" && \
`# clean retrieved resources (does not touch the output)` && \
./run.sh clean

## OR run the subcommands in one go:
# ./run.sh retrieve aggregate clean "${COLLECTION_ID}" 
```


Alternatively you can run the Python script in `image/src` locally.
