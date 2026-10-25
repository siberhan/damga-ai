import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_state_dir() -> Path:
    # Tests point this at a temp folder so they never touch the demo state.
    override = os.environ.get("DAMGA_STATE_DIR")
    state_dir = Path(override) if override else Path(__file__).resolve().parent.parent / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Files ---

def get_file(file_key: str) -> Optional[Dict[str, Any]]:
    path = get_state_dir() / "files" / f"{file_key}.json"
    return _read_json(path)


def list_files() -> List[Dict[str, Any]]:
    files_dir = get_state_dir() / "files"
    if not files_dir.exists():
        return []
    result = []
    for f in sorted(files_dir.glob("*.json")):
        data = _read_json(f)
        if data:
            result.append(data)
    return result


def save_file(file_record: Dict[str, Any]) -> None:
    key = file_record["file_key"]
    path = get_state_dir() / "files" / f"{key}.json"
    _write_json(path, file_record)


# --- Attempts ---

def get_attempt(file_key: str, index: int) -> Optional[Dict[str, Any]]:
    path = get_state_dir() / "attempts" / file_key / f"{index}.json"
    return _read_json(path)


def list_attempts(file_key: str) -> List[Dict[str, Any]]:
    attempts_dir = get_state_dir() / "attempts" / file_key
    if not attempts_dir.exists():
        return []
    attempts = []
    for f in sorted(attempts_dir.glob("*.json"), key=lambda p: int(p.stem) if p.stem.isdigit() else 999):
        data = _read_json(f)
        if data:
            attempts.append(data)
    return attempts


def save_attempt(file_key: str, index: int, attempt_data: Dict[str, Any]) -> None:
    path = get_state_dir() / "attempts" / file_key / f"{index}.json"
    _write_json(path, attempt_data)


# --- Explanations ---

def get_explanations(file_key: str, index: int) -> Dict[str, Any]:
    path = get_state_dir() / "explanations" / file_key / f"{index}.json"
    return _read_json(path) or {}


def save_explanations(file_key: str, index: int, explanations: Dict[str, Any]) -> None:
    path = get_state_dir() / "explanations" / file_key / f"{index}.json"
    _write_json(path, explanations)


# --- Resolutions ---

def get_resolutions(file_key: str, index: int) -> Dict[str, Any]:
    path = get_state_dir() / "resolutions" / file_key / f"{index}.json"
    return _read_json(path) or {}


def save_resolutions(file_key: str, index: int, resolutions: Dict[str, Any]) -> None:
    path = get_state_dir() / "resolutions" / file_key / f"{index}.json"
    _write_json(path, resolutions)


# --- Passports ---

def get_passport(passport_id: int) -> Optional[Dict[str, Any]]:
    path = get_state_dir() / "passports" / f"{passport_id}.json"
    return _read_json(path)


def list_passports() -> List[Dict[str, Any]]:
    pass_dir = get_state_dir() / "passports"
    if not pass_dir.exists():
        return []
    res = []
    for p in sorted(pass_dir.glob("*.json")):
        data = _read_json(p)
        if data:
            res.append(data)
    return res


def save_passport(passport_id: int, passport_data: Dict[str, Any]) -> None:
    path = get_state_dir() / "passports" / f"{passport_id}.json"
    _write_json(path, passport_data)


# --- Docs ---

def save_doc_file(file_key: str, index: int, doc_id: str, pdf_bytes: bytes) -> Path:
    doc_path = get_state_dir() / "docs" / file_key / str(index) / f"{doc_id}.pdf"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_bytes(pdf_bytes)
    return doc_path


def get_doc_file(file_key: str, index: int, doc_id: str) -> Optional[Path]:
    doc_path = get_state_dir() / "docs" / file_key / str(index) / f"{doc_id}.pdf"
    if doc_path.exists():
        return doc_path
    return None
