#!/usr/bin/env python3
"""
Damga AI — independent passport check (spec section 11).

Reads one passport from the Sepolia DamgaRegistry and re-checks it from public data only:
the chain, the evidence PDFs in data/cases, and the signed AI result. No private key is needed.

Usage:
    backend/.venv/bin/python scripts/verify.py --passport <id> [--rpc <sepolia rpc url>] [--result <ai_result.json>]

Exit code 0 only when every check passes.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEPLOYMENT = json.loads((ROOT_DIR / "contracts" / "deployments.sepolia.json").read_text())
# A judge needs no .env: the registry address comes from the committed deployment file.
os.environ.setdefault("DAMGA_REGISTRY_ADDRESS", DEPLOYMENT["DamgaRegistry"])

from web3 import Web3  # noqa: E402

from damga.chain import get_contract_abi, recover_typed_signer  # noqa: E402
from damga.hashing import (  # noqa: E402
    compute_declaration_hash,
    compute_doc_hash,
    compute_docs_root,
    compute_input_hash,
    compute_result_hash,
)
from damga.pipeline import replay_pipeline  # noqa: E402
from damga.sector import load_sector_pack  # noqa: E402

PASSPORT_STATUS = ["NONE", "ACTIVE", "REVOKED", "DISPUTED", "SUPERSEDED"]
CIRCUITS = {"emissions": "emissions_le_limit", "scrap": "scrap_share_ge"}

failures = []


def check(label, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(label)
    return ok


def hx(b):
    return "0x" + bytes(b).hex()


def find_ai_result(result_hash, explicit):
    """The AI result JSON is off-chain. Find the one whose hash the chain sealed."""
    paths = [Path(explicit)] if explicit else (
        list((BACKEND_DIR / "state" / "attempts").rglob("*.json")) + list((ROOT_DIR / "data" / "precomputed").rglob("*.json"))
    )
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and str(data.get("result_hash", "")).lower() == result_hash.lower():
            return p, data
    return None, None


def to_snarkjs(u8):
    """uint256[8] as the Solidity verifier takes it (G2 pairs reversed) back to snarkjs proof.json."""
    s = [str(x) for x in u8]
    return {
        "pi_a": [s[0], s[1], "1"],
        "pi_b": [[s[3], s[2]], [s[5], s[4]], ["1", "0"]],
        "pi_c": [s[6], s[7], "1"],
        "protocol": "groth16",
        "curve": "bn128",
    }


def snarkjs_verify(circuit, u8, public):
    with tempfile.TemporaryDirectory() as d:
        proof_p, pub_p = Path(d) / "proof.json", Path(d) / "public.json"
        proof_p.write_text(json.dumps(to_snarkjs(u8)))
        pub_p.write_text(json.dumps([str(x) for x in public]))
        proc = subprocess.run(
            ["node", str(ROOT_DIR / "zk" / "scripts" / "verify.js"), circuit, str(proof_p), str(pub_p)],
            cwd=str(ROOT_DIR / "zk"), capture_output=True, text=True, timeout=60,
        )
        return proc.returncode == 0 and "PASS" in proc.stdout


def main():
    ap = argparse.ArgumentParser(description="Independently verify a Damga passport on Sepolia")
    ap.add_argument("--passport", type=int, required=True)
    ap.add_argument("--rpc", default=os.environ.get("SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com"))
    ap.add_argument("--result", help="Path to the AI result JSON (found automatically when omitted)")
    args = ap.parse_args()

    w3 = Web3(Web3.HTTPProvider(args.rpc, request_kwargs={"timeout": 30}))
    reg = w3.eth.contract(address=Web3.to_checksum_address(DEPLOYMENT["DamgaRegistry"]), abi=get_contract_abi())
    pid = args.passport

    print(f"Damga passport #{pid} on Sepolia, registry {reg.address}\n")

    # 1. What the chain says
    print("1. Chain record")
    total = reg.functions.totalPassports().call()
    if not check("passport exists", 1 <= pid <= total, f"{total} passports issued"):
        return 1
    (file_key, attempt_index, version, prev_id, verifier, docs_root, result_hash, em_comm, sc_comm,
     em_limit, min_share, model_hash, ruleset_hash, vc_hash, status, issued_at) = reg.functions.getPassport(pid).call()
    file_key, docs_root, result_hash = hx(file_key), hx(docs_root), hx(result_hash)
    print(f"     file {file_key}, attempt {attempt_index}, version {version}, status {PASSPORT_STATUS[status]}")
    check("passport is active", status == 1, PASSPORT_STATUS[status])
    attempts = reg.functions.getAttempts(file_key).call()
    check("attempt count on chain", attempt_index < len(attempts), f"{len(attempts)} attempts sealed for this file")
    att = attempts[attempt_index]
    check("passport docsRoot = sealed attempt docsRoot", hx(att[0]) == docs_root)
    check("passport resultHash = sealed attempt resultHash", hx(att[5]) == result_hash)
    check("model approved on chain", reg.functions.approvedModels(model_hash).call(), hx(model_hash))
    check("ruleset approved on chain", reg.functions.approvedRulesets(ruleset_hash).call(), hx(ruleset_hash))
    v_active, v_name = reg.functions.verifiers(verifier).call()
    check("verifier is registered and active", v_active, f"{v_name} {verifier}")

    # 2. The issuing transaction: proofs and the verifier's signature
    print("\n2. Zero-knowledge proofs (re-verified locally with snarkjs and the published vkeys)")
    logs = reg.events.PassportIssued().get_logs(
        from_block=w3.eth.get_transaction_receipt(DEPLOYMENT["deployTx"])["blockNumber"],
        argument_filters={"passportId": pid},
    )
    if not check("PassportIssued event found", len(logs) == 1):
        return 1
    tx = w3.eth.get_transaction(logs[0]["transactionHash"])
    print(f"     tx https://sepolia.etherscan.io/tx/{hx(logs[0]['transactionHash'])}")
    _, call = reg.decode_function_input(tx["input"])
    v = call["v"]
    check("emissions proof: committed value <= limit",
          snarkjs_verify(CIRCUITS["emissions"], call["emissionsProof"], [em_comm, em_limit]),
          f"limit {em_limit} kg CO2/t")
    check("scrap proof: committed share >= minimum",
          snarkjs_verify(CIRCUITS["scrap"], call["scrapProof"], [sc_comm, min_share]),
          f"min {min_share / 10:g}%")
    v_msg = {
        "fileKey": hx(v["fileKey"]), "attemptIndex": v["attemptIndex"], "docsRoot": hx(v["docsRoot"]),
        "resultHash": hx(v["resultHash"]), "resolutionsHash": hx(v["resolutionsHash"]),
        "redResolved": v["redResolved"], "yellowChecked": v["yellowChecked"],
        "emissionsCommitment": v["emissionsCommitment"], "scrapCommitment": v["scrapCommitment"],
        "emissionsLimit": v["emissionsLimit"], "minScrapShare": v["minScrapShare"], "vcHash": hx(v["vcHash"]),
    }
    signer = recover_typed_signer("Verification", v_msg, hx(call["verifierSig"]), reg.address)
    check("verifier signature recovers to the passport verifier", signer.lower() == verifier.lower(), signer)

    # 3. Off-chain evidence against the sealed hashes
    print("\n3. Evidence and AI result (off-chain files against the sealed hashes)")
    path, result = find_ai_result(result_hash, args.result)
    if not check("signed AI result found", result is not None, str(path) if path else "pass --result"):
        return finish()
    check("AI result hashes to the sealed resultHash", compute_result_hash(result) == result_hash)
    case_dir = ROOT_DIR / "data" / "cases" / result.get("case_id", "")
    doc_hashes = []
    for ext in result.get("extractions", []):
        pdf = case_dir / "docs" / f"{ext['doc_id']}.pdf"
        actual = compute_doc_hash(pdf.read_bytes()) if pdf.exists() else None
        check(f"document {ext['doc_id']} unchanged", actual == ext["doc_sha256"])
        doc_hashes.append(actual or "0x" + "00" * 32)
    local_root = compute_docs_root(doc_hashes)
    check("docsRoot recomputed from the PDF bytes", local_root == docs_root)
    check("docsRoot matches the contract's own computeDocsRoot",
          hx(reg.functions.computeDocsRoot([bytes.fromhex(h[2:]) for h in doc_hashes]).call()) == docs_root)
    declaration = json.loads((case_dir / "declaration.json").read_text(encoding="utf-8"))
    decl_hash = compute_declaration_hash(declaration)
    check("declarationHash = sealed attempt", decl_hash == hx(att[1]))
    check("inputHash = keccak(docsRoot, declarationHash)", compute_input_hash(docs_root, decl_hash) == hx(att[2]))
    ai_signer = recover_typed_signer("AIAttestation", result["attestation"], result["signature"]["sig"], reg.address)
    check("AI attestation signer is an approved AI signer on chain", reg.functions.aiSigners(ai_signer).call(), ai_signer)

    # 4. Deterministic replay: the code math and rules give the same answer from the same quotes
    print("\n4. Replay (no AI call: emissions math and rules from the stored, quote-checked extractions)")
    sector_data, ruleset_hash_local = load_sector_pack()
    check("local ruleset hash = sealed ruleset", ruleset_hash_local == hx(ruleset_hash))
    replayed = replay_pipeline(copy.deepcopy(result), declaration, sector_data)
    check("emissions replay", replayed["emissions"] == result["emissions"],
          f"{replayed['emissions']['direct_kg_per_t']} kg CO2/t")
    check("flags replay", replayed["flags"] == result["flags"] and replayed["counts"] == result["counts"],
          f"red {replayed['counts']['red']}, yellow {replayed['counts']['yellow']}, missing {replayed['counts']['missing']}")
    check("replayed resultHash = sealed resultHash", replayed["result_hash"] == result_hash)
    return finish()


def finish():
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): " + "; ".join(failures))
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
