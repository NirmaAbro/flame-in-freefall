"""Where T6 keeps its files, and how it writes them safely.

data/raw/                 the PSI tables, as downloaded
data/mappings/<id>.json   one mapping file per table; T2 reads the approved ones
data/proposals/           untouched copies of the model's proposals, for the score
data/gold/mappings/       mappings written by hand, the reference for the score
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from app.schemas import MappingFile

from .tables import TableError

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def mapping_path(data_dir, source_id: str) -> Path:
    return Path(data_dir) / "mappings" / f"{source_id}.json"


def gold_dir(data_dir) -> Path:
    return Path(data_dir) / "gold" / "mappings"


def proposals_dir(data_dir) -> Path:
    return Path(data_dir) / "proposals"


def find_table(data_dir, source_id: str) -> Path:
    """The table file of one PSI id in data/raw/, for example PSI-25_Experimental table_BASS-II.csv."""
    matches = sorted((Path(data_dir) / "raw").glob(f"{source_id}_*.csv"))
    if not matches:
        raise TableError(f"No table file for {source_id} in data/raw/. Its name must start with '{source_id}_' and end with '.csv'.")
    if len(matches) > 1:
        raise TableError(f"More than one table file for {source_id} in data/raw/: {', '.join(path.name for path in matches)}")
    return matches[0]


def read_mapping(path) -> MappingFile:
    return MappingFile.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def write_json_atomic(path, payload: dict) -> None:
    """Write the whole file or nothing: a failure leaves an existing file as it was."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def new_proposal_path(data_dir, source_id: str, stamp: str) -> Path:
    """A name that sorts by time and never replaces an older copy."""
    number = 0
    while True:
        path = proposals_dir(data_dir) / f"{source_id}.{stamp}.{number:02d}.json"
        if not path.exists():
            return path
        number += 1


def latest_proposal(data_dir, source_id: str) -> Optional[Path]:
    copies = sorted(proposals_dir(data_dir).glob(f"{source_id}.*.json"))
    return copies[-1] if copies else None
