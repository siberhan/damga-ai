import hashlib
import json
import pytest
from eth_utils import keccak
from damga.hashing import (
    canonical_json,
    clean_hex,
    compute_declaration_hash,
    compute_doc_hash,
    compute_docs_root,
    compute_file_key,
    compute_input_hash,
    compute_model_hash,
    compute_plant_id,
    compute_result_hash,
    compute_ruleset_hash,
    sha256_bytes32,
)


def test_canonical_json():
    # Key sorting and compact separators
    d1 = {"b": 2, "a": 1, "c": [3, 2, 1]}
    d2 = {"a": 1, "c": [3, 2, 1], "b": 2}
    assert canonical_json(d1) == canonical_json(d2)
    assert canonical_json(d1) == b'{"a":1,"b":2,"c":[3,2,1]}'


def test_sha256_bytes32():
    data = b"hello world"
    h = sha256_bytes32(data)
    assert h.startswith("0x")
    assert len(h) == 66
    assert h == "0x" + hashlib.sha256(data).hexdigest()


def test_compute_plant_id():
    pid = "TR-ALIAGA-DEMO-001"
    h = compute_plant_id(pid)
    assert h.startswith("0x")
    assert len(h) == 66
    assert h == "0x" + keccak(pid.encode("utf-8")).hex()


def test_compute_file_key():
    plant_hex = compute_plant_id("TR-ALIAGA-DEMO-001")
    fk1 = compute_file_key(plant_hex, 2026, 72142000)
    fk2 = compute_file_key(plant_hex, 2026, "72142000")
    assert fk1 == fk2
    assert fk1.startswith("0x")
    assert len(fk1) == 66


def test_docs_root_single_leaf():
    # 1 leaf: docsRoot equals the leaf hash keccak256(docHash)
    doc_hash = "0x" + "11" * 32
    root = compute_docs_root([doc_hash])
    leaf = "0x" + keccak(bytes.fromhex("11" * 32)).hex()
    assert root == leaf


def test_docs_root_two_leaves():
    h1 = "0x" + "11" * 32
    h2 = "0x" + "22" * 32
    root1 = compute_docs_root([h1, h2])
    root2 = compute_docs_root([h2, h1])
    # Order-independent root because leaves are sorted ascending
    assert root1 == root2
    assert len(root1) == 66


def test_docs_root_three_leaves():
    hashes = ["0x" + f"{i:02x}" * 32 for i in [1, 2, 3]]
    root = compute_docs_root(hashes)
    assert root.startswith("0x")
    assert len(root) == 66

    # Verify odd leaf carried up:
    leaves = sorted([keccak(bytes.fromhex(f"{i:02x}" * 32)) for i in [1, 2, 3]])
    a, b = leaves[0], leaves[1]
    if a > b:
        a, b = b, a
    p1 = keccak(a + b)
    p2 = leaves[2]  # carried up
    if p1 > p2:
        p1, p2 = p2, p1
    expected_root = "0x" + keccak(p1 + p2).hex()
    assert root == expected_root


def test_docs_root_five_leaves():
    hashes = ["0x" + f"{i:02x}" * 32 for i in range(1, 6)]
    root = compute_docs_root(hashes)
    assert root.startswith("0x")
    assert len(root) == 66

    # Repeat with shuffled hashes, result must be identical
    shuffled = [hashes[3], hashes[0], hashes[4], hashes[1], hashes[2]]
    assert compute_docs_root(shuffled) == root


def test_compute_input_hash():
    docs_root = "0x" + "aa" * 32
    decl_hash = "0x" + "bb" * 32
    inp = compute_input_hash(docs_root, decl_hash)
    assert inp.startswith("0x")
    assert len(inp) == 66


def test_compute_model_hash():
    mh = compute_model_hash("mistral", "mistral-small-latest", "2026-03")
    assert mh.startswith("0x")
    assert len(mh) == 66


def test_compute_ruleset_hash():
    rh = compute_ruleset_hash(b"id: steel_eaf\nversion: 1.0.0\n")
    assert rh.startswith("0x")
    assert len(rh) == 66


def test_compute_result_hash():
    res = {
        "status": "red",
        "counts": {"red": 1},
        "signature": {"sig": "0x1234"},
    }
    h1 = compute_result_hash(res)
    # Removing signature beforehand gives same result
    res_no_sig = {"status": "red", "counts": {"red": 1}}
    h2 = compute_result_hash(res_no_sig)
    assert h1 == h2
