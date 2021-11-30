import os

DEFAULT_OUTPUT_DIRECTORY = "./output"


def id_to_filename(value):
    return value.replace('/', '_')


def get_mandatory_env_var(name):
    value = os.environ.get(name)
    if value is None:
        print(f"ERROR: mandatory {name} variable not set")
        exit(1)
    return value


def get_optional_env_var(name, default=None):
    value = os.environ.get(name)
    if value is None:
        return default
    else:
        return value


def get_metadata_dir(basedir, collection_id):
    return f"{basedir}/{collection_id}/metadata"


def get_fulltext_dir(basedir, collection_id):
    return f"{basedir}/{collection_id}/fulltext"
