# Europeana fulltext resource aggregation
Usage with docker:

```shell
docker-compose build #only before first run

cp .env-template .env
vi .env # or editor of choice :)
# configure Europeana API key and optionally a custom output directory

docker-compose run europeana-aggregator 9200301 #or another collection with full text content to aggregate metadata and content for
```

Alternatively you can run the Python script in `image/src` locally.
Make sure to set the following environment variables:
- `SEARCH_API_URL` - base URL of the Europeana Search API
- `SEARCH_API_KEY` - personal key that gives access to the Europeana Search API
- `IIIF_API_URL` - base URL of the Europeana IIIF service
- `OUTPUT_DIR` - target directory for retrieved content
