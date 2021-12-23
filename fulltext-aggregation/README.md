# Europeana fulltext resource aggregation
Usage with docker:

```shell
bash build.sh #only before first run

cp .env-template .env
vi .env # or editor of choice :)
# configure a local output directory and other (optional) settings

COLLECTION_ID=...... # for instance '9200396'

`# retrieve metadata dump from server` && \
./run.sh retrieve "${COLLECTION_ID}" && \
`# run aggregation scripts` && \ 
./run.sh aggregate "${COLLECTION_ID}" && \
`# clean retrieved resources (does not touch the output)` && \
./run.sh clean
```

Alternatively you can run the Python script in `image/src` locally.
