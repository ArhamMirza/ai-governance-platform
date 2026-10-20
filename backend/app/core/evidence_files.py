"""Where an uploaded file is on disk.

The database remembers a file by its stored name, not by where the folder was
when it was uploaded: the folder is a setting (EVIDENCE_STORAGE_DIR), and a
database restored on another machine, or into another directory, must still
find its files. Rows written before this stored the whole path, so only the
last part of whatever is recorded is used -- split on either kind of slash, as
a row written on Windows may be read on Linux.
"""

import re
from pathlib import Path

from app.core.config import get_settings


def stored_name(recorded: str) -> str:
    return re.split(r"[\\/]", recorded)[-1]


def directory() -> Path:
    return Path(get_settings().evidence_storage_dir)


def path_for(recorded: str) -> Path:
    return directory() / stored_name(recorded)
