import logging

from glom import glom, flatten, PathAccessError
from multiprocessing import Pool

from common import get_json_from_http
from env import IIIF_API_URL, THREAD_POOL_SIZE

logger = logging.getLogger(__name__)


def retrieve_annotation_refs(iiif_manifest_url, session):
    if not iiif_manifest_url.startswith(IIIF_API_URL):
        logger.warning(f"Skipping URL, not a IIIF service URL: {iiif_manifest_url}")
        return []

    logger.debug(f"Getting manifest from {iiif_manifest_url}")
    manifest = get_json_from_http(iiif_manifest_url, session)

    if manifest is None:
        logger.warning(f"No valid response from manifest request at {iiif_manifest_url}")
    else:
        with Pool(THREAD_POOL_SIZE) as p:
            # collection annotation URLs for record
            canvases = glom(manifest, ('sequences', ['canvases']), skip_exc=PathAccessError)
            if canvases is not None:
                annotation_urls = glom(flatten(canvases), ['otherContent'], skip_exc=PathAccessError)
                if annotation_urls is not None:
                    annotation_urls_flat = flatten(annotation_urls)
                    logger.debug(f"{len(annotation_urls_flat)} annotation references found")

                    retrieval_context = RetrievalContext(session)
                    # retrieval of fulltext URLs in thread pool
                    fulltext_urls = p.map(retrieval_context.retrieve_fulltext_refs_from_annotation, annotation_urls_flat)
                    return [url for url in fulltext_urls if fulltext_urls is not None]
    return []


class RetrievalContext:

    def __init__(self, session):
        self.session = session

    def retrieve_fulltext_refs_from_annotation(self, annotation_url):
        refs = []
        annotations = get_json_from_http(annotation_url, self.session)
        if annotations is None:
            logger.error(f"No content for annotations at {annotation_url}")
        else:
            fulltext_ref = get_fulltext_ref_from_annotations(annotations)
            if fulltext_ref is None:
                logger.warning(f"No full text content in annotations data at {annotation_url}")

            return fulltext_ref


def get_fulltext_ref_from_annotations(annotations):
    resources = annotations.get('resources', None)
    if resources is not None:
        for resource in resources:
            if resource['dcType'] == 'Page':
                return glom(resource, 'resource.@id', skip_exc=PathAccessError)

    return None

