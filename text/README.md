# Retrieval and extraction of Europeana newspaper full text content
Produces plain text (.txt) files for Europeana Newspapers full text content made available
by Europeana as [dumps](https://pro.europeana.eu/page/iiif#download).

Usage with docker:

```shell
COLLECTION_ID='9200396' #or another identifier listed on the dumps page (see link above)

bash build.sh # only before first run or after an update of the sources

## optional: tweak settings (local output directory, memory usage, debug mode)
cp .env-template .env
vi .env # or editor of choice :)

# retrieve metadata dump from server
./run.sh "${COLLECTION_ID}"
```

Alternatively you can run the Python script in `image/src` locally.

There is also a script `run-all.sh` that will retrieve and extract text for all 
collections. Be aware that this will take a long time (hours to days) and use up a lot
of storage - you will need ~100GB free disk space. Make and tweak a `.env` file before
running as described above.
