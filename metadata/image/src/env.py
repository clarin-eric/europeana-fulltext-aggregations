from common import get_optional_env_var, get_mandatory_env_var

# Mandatory variables
RECORD_API_KEY = get_mandatory_env_var(
    'RECORD_API_KEY')
CMDI_RECORDS_BASE_URL = get_mandatory_env_var(
    'CMDI_RECORDS_BASE_URL')

# Optional variables

COLLECTION_DISPLAY_NAME = get_optional_env_var(
    'COLLECTION_DISPLAY_NAME',
    'Europeana newspapers full-text')
IIIF_API_URL = get_optional_env_var(
    'IIIF_API_URL',
    'https://iiif.europeana.eu')
LANDING_PAGE_URL = get_optional_env_var(
    'LANDING_PAGE_URL',
    'https://pro.europeana.eu/page/iiif#download')
RECORD_API_URL = get_optional_env_var(
    'RECORD_API_URL',
    'https://api.europeana.eu/record/v2')
FILE_PROCESSING_THREAD_POOL_SIZE = int(get_optional_env_var(
    'FILE_PROCESSING_THREAD_POOL_SIZE',
    '5'))
API_RETRIEVAL_THREAD_POOL_SIZE = int(get_optional_env_var(
    'API_RETRIEVAL_THREAD_POOL_SIZE',
    '1'))
PRETTY_CMDI_XML = 'TRUE' == get_optional_env_var(
    'PRETTY_CMDI_XML',
    "False").upper()
