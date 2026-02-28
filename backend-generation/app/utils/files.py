import json
import secrets
import string
from pathlib import Path
from typing import Any


REQUEST_ID_ALPHABET = string.ascii_lowercase + string.digits


def make_request_id(length: int = 8) -> str:
    return "".join(secrets.choice(REQUEST_ID_ALPHABET) for _ in range(length))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
