import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import yaml
from damga.hashing import compute_ruleset_hash


def get_default_sector_path() -> Path:
    """Finds the default steel_eaf.yaml path, preferring sectors/ if it exists, falling back to fixture."""
    backend_dir = Path(__file__).resolve().parent.parent
    root_dir = backend_dir.parent

    real_path = root_dir / "sectors" / "steel_eaf.yaml"
    if real_path.exists():
        return real_path

    fixture_path = backend_dir / "tests" / "fixtures" / "steel_eaf.yaml"
    return fixture_path


def load_sector_pack(path: Optional[str | Path] = None) -> Tuple[Dict[str, Any], str]:
    """
    Loads the sector pack YAML.
    Returns (parsed_data_dict, ruleset_hash).
    """
    target_path = Path(path) if path else get_default_sector_path()
    if not target_path.exists():
        raise FileNotFoundError(f"Sector pack file not found: {target_path}")

    raw_bytes = target_path.read_bytes()
    ruleset_hash = compute_ruleset_hash(raw_bytes)
    data = yaml.safe_load(raw_bytes.decode("utf-8"))
    return data, ruleset_hash
