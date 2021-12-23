import logging

from glom import glom, flatten, PathAccessError
from common import get_json_from_http
from common import get_optional_env_var

logger = logging.getLogger(__name__)

IIIF_API_URL = get_optional_env_var('IIIF_API_URL', 'https://iiif.europeana.eu')


def retrieve_annotation_refs(iiif_manifest_url, session):
    if not iiif_manifest_url.startswith(IIIF_API_URL):
        logger.warning(f"Skipping URL, not a IIIF service URL: {iiif_manifest_url}")
        return []

    logger.debug(f"Getting manifest from {iiif_manifest_url}")
    manifest = get_json_from_http(iiif_manifest_url, session)

    if manifest is None:
        logger.warning(f"No valid response from manifest request at {iiif_manifest_url}")
    else:
        # collection annotation URLs for record
        canvases = glom(manifest, ('sequences', ['canvases']), skip_exc=PathAccessError)
        if canvases is not None:
            annotation_urls = glom(flatten(canvases), ['otherContent'], skip_exc=PathAccessError)
            if annotation_urls is not None:
                annotation_urls_flat = flatten(annotation_urls)
                logger.debug(f"{len(annotation_urls_flat)} annotation references found")
                return retrieve_fulltext_refs(annotation_urls_flat, session)

    return []


def retrieve_fulltext_refs(annotation_urls, session=None):
    refs = []
    for annotation_url in annotation_urls:
        annotations = get_json_from_http(annotation_url, session)
        if annotations is None:
            logger.error(f"No content for annotations at {annotation_url}")
        else:
            fulltext_ref = get_fulltext_ref_from_annotations(annotations)
            if fulltext_ref is None:
                logger.warning(f"No full text content in annotations data at {annotation_url}")
            else:
                refs += [fulltext_ref]

    return refs


def get_fulltext_ref_from_annotations(annotations):
    resources = annotations.get('resources', None)
    if resources is not None:
        for resource in resources:
            if resource['dcType'] == 'Page':
                return glom(resource, 'resource.@id', skip_exc=PathAccessError)

    return None

