import json
from pathlib import Path
import pytest
from damga.chain import recover_typed_signer, sign_ai_attestation
from damga.hashing import compute_result_hash
from damga.pipeline import get_project_root, replay_pipeline
from damga.sector import load_sector_pack


def test_pipeline_replay_determinism():
    sector_data, ruleset_hash = load_sector_pack()
    root = get_project_root()
    example_path = root / "spec" / "examples" / "ai_result.example.json"
    decl_path = root / "spec" / "examples" / "declaration.example.json"

    assert example_path.exists(), "ai_result.example.json must exist"
    assert decl_path.exists(), "declaration.example.json must exist"

    stored_result = json.loads(example_path.read_text(encoding="utf-8"))
    declaration = json.loads(decl_path.read_text(encoding="utf-8"))

    # Replay twice
    replayed1 = replay_pipeline(stored_result, declaration, sector_data)
    replayed2 = replay_pipeline(stored_result, declaration, sector_data)

    hash1 = compute_result_hash(replayed1)
    hash2 = compute_result_hash(replayed2)

    assert hash1 == hash2, "Replay pipeline must produce identical resultHash every time"
    assert replayed1["result_hash"] == replayed2["result_hash"]
    assert replayed1["status"] == replayed2["status"]
    assert replayed1["counts"] == replayed2["counts"]
    assert replayed1["emissions"]["direct_kg_per_t"] == replayed2["emissions"]["direct_kg_per_t"]


def test_ai_attestation_signing_and_recovery():
    attestation = {
        "fileKey": "0x" + "11" * 32,
        "inputHash": "0x" + "22" * 32,
        "modelHash": "0x" + "33" * 32,
        "rulesetHash": "0x" + "44" * 32,
        "resultHash": "0x" + "55" * 32,
        "status": 2,
        "redCount": 1,
        "yellowCount": 0,
        "missingCount": 0,
        "confidenceBps": 9400,
    }

    signer_addr, sig = sign_ai_attestation(attestation)
    assert signer_addr.startswith("0x")
    assert sig.startswith("0x")

    recovered = recover_typed_signer("AIAttestation", attestation, sig)
    assert recovered.lower() == signer_addr.lower()
