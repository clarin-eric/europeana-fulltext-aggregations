# Europeana fulltext resource aggregation
Produces [CMDI](https://www.clarin.eu/cmdi) metadata for Europeana Newspapers full text content made available via 
[dumps](https://pro.europeana.eu/page/iiif#download) and an
[API](https://github.com/europeana/fulltext) (deployed at https://iiif.europeana.eu).

The produced metadata groups Europeana records by newspaper title and year of publication. CMDI records are created for
a title/year combination, and if multiple years are available for a title, a parent record for the title is also 
created. The title/year specific records refer to full text annotations at the page level in JSON format.

The aggregation scripts operate on a 'collection', which are identified by a numeric collection identifier issued by
Europeana (see the [dumps](https://pro.europeana.eu/page/iiif#download).

To use these scripts, you will need to obtain a Europeana API key, which can be requested
[here](https://pro.europeana.eu/page/apis).   

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
