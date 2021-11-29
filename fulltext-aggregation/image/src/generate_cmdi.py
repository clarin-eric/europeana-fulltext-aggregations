import logging
import glom

logger = logging.getLogger(__name__)


def generate(metadata_dir, fulltext_dir):
    logging.basicConfig()
    logger.setLevel(logging.INFO)
