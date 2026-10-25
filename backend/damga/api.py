from datetime import datetime, timezone
import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from damga.chain import (
    get_eip712_domain,
    get_registry_address,
    get_typed_data_payload,
    is_offline,
    recover_typed_signer,
    sign_verification,
)
from damga.emissions import calculate_emissions
from damga.hashing import (
    canonical_json,
    compute_declaration_hash,
    compute_doc_hash,
    compute_docs_root,
    compute_file_key,
    compute_input_hash,
    compute_plant_id,
    compute_resolutions_hash,
    compute_result_hash,
    compute_vc_hash,
)
from damga.pipeline import get_project_root, run_pipeline
from damga.rules import evaluate_rules
from damga.sector import load_sector_pack
import damga.onchain as onchain
import damga.store as store
from damga.zk import compute_poseidon_commitment, generate_proof

# Groth16 inputs live in the BN254 scalar field.
BN254_FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617

app = FastAPI(title="Damga AI API", version="0.1.0")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class RegisterFileRequest(BaseModel):
    plant_id: str = "TR-ALIAGA-DEMO-001"
    year: int = 2026
    cn_code: str = "72142000"


class ExplanationRequest(BaseModel):
    attempt_index: int
    explanations: Dict[str, str]


class SendRequest(BaseModel):
    attempt_index: int


class ResolutionRequest(BaseModel):
    red: Dict[str, str] = {}
    yellow_checked: List[str] = []


class VerifyRequest(BaseModel):
    signature: Optional[str] = None
    demo_signer: bool = False


# --- Endpoints ---

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "damga-ai-backend",
        "version": "0.1.0",
        "chain_mode": "offline" if is_offline() else "online",
        "ai_mode": os.environ.get("AI_MODE", "precomputed"),
        "registry_address": get_registry_address() or None,
    }


@app.get("/api/cases")
def list_demo_cases():
    root = get_project_root()
    cases_dir = root / "data" / "cases"
    result = []

    if cases_dir.exists():
        for cdir in sorted(cases_dir.iterdir()):
            if cdir.is_dir():
                truth_path = cdir / "truth.json"
                desc = "Demo case"
                badge = "info"
                if truth_path.exists():
                    t = json.loads(truth_path.read_text(encoding="utf-8"))
                    desc = t.get("cheat", desc)
                    badge = t.get("expected_status", "info")
                result.append({
                    "id": cdir.name,
                    "name": cdir.name.replace("-", " ").title(),
                    "description": desc,
                    "badge": badge,
                })

    if not result:
        result = [
            {"id": "honest-01", "name": "Honest Plant - Clean Case", "description": "All documents match declaration exactly; green status.", "badge": "green"},
            {"id": "cheat-pigiron-invoice-01", "name": "Omitted Pig Iron Invoice", "description": "Declaration omits 800 t pig iron invoice found in docs (red).", "badge": "red"},
            {"id": "cheat-material-balance-01", "name": "Impossible Metal Yield", "description": "Output exceeds physical metal inputs outside BREF range (red).", "badge": "red"},
            {"id": "missing-gas-bill-01", "name": "Missing Monthly Bills", "description": "Only 10 of 12 required monthly gas bills uploaded (missing).", "badge": "missing"},
            {"id": "injection-attack-01", "name": "Prompt Injection in Scrap Invoice", "description": "Document attempts prompt injection; screened and flagged yellow.", "badge": "yellow"},
        ]

    return result


@app.post("/api/files")
def create_file(req: RegisterFileRequest):
    plant_id_hex = compute_plant_id(req.plant_id)
    file_key = compute_file_key(plant_id_hex, req.year, req.cn_code)

    existing = store.get_file(file_key)
    if existing:
        return existing

    register_tx = None
    if not is_offline():
        try:
            register_tx = onchain.register_file(plant_id_hex, req.year, req.cn_code)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Sepolia registerFile failed: {e}")

    file_record = {
        "file_key": file_key,
        "plant": {
            "plant_id": req.plant_id,
            "name": "Aliağa Demo Steel Works (fictional)",
            "country": "TR",
            "city": "Aliağa, İzmir",
            "installation_name": "Melt shop and rolling mill",
        },
        "year": req.year,
        "product": {
            "cn_code": str(req.cn_code),
            "name": "Rebar",
            "gtin": "00200000000014",
            "lot": f"{req.year}-{req.cn_code}",
        },
        "state": "draft",
        "status": "green",
        "attempt_count": 0,
        "passport_id": None,
        "register_tx": register_tx,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    store.save_file(file_record)
    return file_record


@app.get("/api/files")
def get_files():
    files = store.list_files()
    if not files:
        # Pre-seed a default demo file summary if state is fresh
        default_fk = compute_file_key(compute_plant_id("TR-ALIAGA-DEMO-001"), 2026, "72142000")
        sample_file = {
            "file_key": default_fk,
            "plant": {
                "plant_id": "TR-ALIAGA-DEMO-001",
                "name": "Aliağa Demo Steel Works (fictional)",
                "country": "TR",
                "city": "Aliağa, İzmir",
            },
            "year": 2026,
            "product": {
                "cn_code": "72142000",
                "name": "Rebar",
                "gtin": "00200000000014",
                "lot": "2026-72142000",
            },
            "state": "draft",
            "status": "green",
            "attempt_count": 0,
            "passport_id": None,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        store.save_file(sample_file)
        files = [sample_file]
    return files


@app.get("/api/files/{file_key}")
def get_file_detail(file_key: str):
    file_record = store.get_file(file_key)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    raw_attempts = store.list_attempts(file_key)
    attempts = []
    red_count = 0

    for idx, att in enumerate(raw_attempts):
        st = att.get("status", "green")
        if st == "red":
            red_count += 1
        flags = att.get("flags", [])
        # Apply explanations if stored
        explanations = store.get_explanations(file_key, idx)
        resolutions = store.get_resolutions(file_key, idx)
        red_res = resolutions.get("red", {})
        yellow_chk = set(resolutions.get("yellow_checked", []))

        updated_flags = []
        for flg in flags:
            flg_copy = dict(flg)
            fid = flg_copy.get("id")
            if fid in explanations:
                flg_copy["exporter_explanation"] = explanations[fid]
            if fid in red_res:
                flg_copy["state"] = "resolved"
                flg_copy["resolution"] = red_res[fid]
            if fid in yellow_chk:
                flg_copy["checked"] = True
                flg_copy["state"] = "checked"
            updated_flags.append(flg_copy)

        documents_meta = []
        for ext in att.get("extractions", []):
            did = ext.get("doc_id", "")
            documents_meta.append({
                "doc_id": did,
                "type": ext.get("doc_type", ""),
                "period": ext.get("period") or str(file_record.get("year", "")),
                "sha256": ext.get("doc_sha256", ""),
                "url": f"/api/docs/{file_key}/{idx}/{did}",
            })

        attempt_model = att.get("model", {})

        attempts.append({
            "index": idx,
            "status": st,
            "legacy": bool(att.get("legacy")),
            "note": att.get("note"),
            "counts": att.get("counts", {"red": 0, "yellow": 0, "missing": 0}),
            "direct_kg_per_t": att.get("emissions", {}).get("direct_kg_per_t", 92),
            "submitted_at": att.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
            "tx_hash": att.get("tx_hash"),
            "etherscan": f"https://sepolia.etherscan.io/tx/{att['tx_hash']}" if att.get("tx_hash") else None,
            "result_hash": att.get("result_hash", ""),
            "docs_root": att.get("docs_root", ""),
            "flags": updated_flags,
            "documents": documents_meta,
            "extractions": att.get("extractions", []),
            "totals": att.get("totals", {}),
            "emissions": att.get("emissions", {}),
            "model": attempt_model,
            "ruleset_version": att.get("ruleset", {}).get("version", "1.0.0"),
            "confidence_bps": att.get("confidence_bps", 9400),
        })

    summary_msg = f"{len(attempts)} attempt(s)"
    if red_count > 0:
        summary_msg += f", {red_count} failed (red)."
    else:
        summary_msg += ", ready for review."

    return {
        "file_key": file_key,
        "plant": file_record.get("plant"),
        "year": file_record.get("year"),
        "product": file_record.get("product"),
        "state": file_record.get("state", "draft"),
        "passport_id": file_record.get("passport_id"),
        "attempts": attempts,
        "history_summary": summary_msg,
    }


@app.post("/api/files/{file_key}/attempts")
async def submit_attempt(
    request: Request,
    file_key: str,
):
    file_record = store.get_file(file_key)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # The web client sends {"case_id": ...} as JSON; curl users may send a form.
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    else:
        body = dict(await request.form())
    case_id = body.get("case_id")
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required (one of /api/cases)")

    root = get_project_root()
    case_dir = root / "data" / "cases" / case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    # The AI result does not depend on the attempt index, so one precomputed signed
    # result per case can be submitted as any attempt of its file.
    live = os.environ.get("AI_MODE", "precomputed") == "live"
    ai_result = run_pipeline(case_dir, attempt_index=0, live=live)
    if ai_result.get("file_key") != file_key:
        raise HTTPException(status_code=400, detail="This case belongs to a different plant/year/product file")

    attempt_index = len(store.list_attempts(file_key))
    ai_result["attempt_index"] = attempt_index
    ai_result["tx_hash"] = None
    ai_result["etherscan"] = None

    if not is_offline():
        try:
            sent = onchain.submit_attempt(ai_result)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Sepolia submitAttempt failed: {e}")
        if sent["chain_attempt_index"] != attempt_index:
            raise HTTPException(status_code=409, detail="Local attempt list is out of sync with the chain")
        ai_result["tx_hash"] = sent["tx_hash"]
        ai_result["etherscan"] = f"https://sepolia.etherscan.io/tx/{sent['tx_hash']}"

    store.save_attempt(file_key, attempt_index, ai_result)

    file_record["state"] = "attempt_submitted"
    file_record["status"] = ai_result["status"]
    file_record["attempt_count"] = attempt_index + 1
    file_record["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    store.save_file(file_record)

    return ai_result


@app.post("/api/files/{file_key}/explanations")
def save_explanations_endpoint(file_key: str, req: ExplanationRequest):
    store.save_explanations(file_key, req.attempt_index, req.explanations)
    return get_file_detail(file_key)


@app.post("/api/files/{file_key}/send")
def send_to_verifier(file_key: str, req: SendRequest):
    file_record = store.get_file(file_key)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    file_record["state"] = "sent_to_verifier"
    file_record["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    store.save_file(file_record)

    return {
        "status": "sent_to_verifier",
        "verifier_link": f"/verifier/files/{file_key}",
    }


@app.get("/api/verifier/queue")
def verifier_queue():
    files = store.list_files()
    queue = [f for f in files if f.get("state") in ("sent_to_verifier", "attempt_submitted", "verified")]
    return queue


@app.post("/api/files/{file_key}/attempts/{i}/resolutions")
def save_resolutions_endpoint(file_key: str, i: int, req: ResolutionRequest):
    store.save_resolutions(file_key, i, {"red": req.red, "yellow_checked": req.yellow_checked})
    return {"status": "ok", "resolutions": {"red": req.red, "yellow_checked": req.yellow_checked}}


def _declaration_for(attempt: Dict[str, Any]) -> Dict[str, Any]:
    path = get_project_root() / "data" / "cases" / attempt.get("case_id", "") / "declaration.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Declaration for this attempt not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _private_path(file_key: str, i: int) -> Path:
    return store.get_state_dir() / "private" / f"{file_key}-{i}.json"


def _prepare_verification(file_key: str, i: int) -> Dict[str, Any]:
    """Creates (once) the salts, commitments, VC and the Verification message for an attempt.

    Salts stay in backend/state/private (gitignored). Only commitments go on-chain.
    """
    attempt = store.get_attempt(file_key, i)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    file_record = store.get_file(file_key)
    resolutions = store.get_resolutions(file_key, i)

    path = _private_path(file_key, i)
    private = store._read_json(path)
    if private is None:
        claims = _declaration_for(attempt).get("zk_claims", {})
        emissions_val = attempt["emissions"]["direct_kg_per_t"]
        scrap_val = attempt["emissions"]["scrap_share_permille"]
        emissions_salt = secrets.randbelow(BN254_FIELD)
        scrap_salt = secrets.randbelow(BN254_FIELD)
        limit = int(claims["emissions_limit_kg_per_t"])
        min_share = int(claims["min_scrap_share_permille"])
        emissions_comm = compute_poseidon_commitment(emissions_val, emissions_salt)
        scrap_comm = compute_poseidon_commitment(scrap_val, scrap_salt)
        lot = f"{file_record['year']}-{file_record['product']['cn_code']}"
        vc = {
            "@context": ["https://www.w3.org/ns/credentials/v2"],
            "type": ["VerifiableCredential", "DamgaSteelPassport"],
            "id": f"urn:damga:passport:{file_key}:{i}",
            "issuer": {"id": "urn:damga:verifier:demo-verification-gmbh", "name": "Demo Verification GmbH (fictional)"},
            "validFrom": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "credentialSubject": {
                "product": {**file_record["product"], "gs1_digital_link": f"/01/00200000000014/10/{lot}"},
                "plant": {"name": file_record["plant"]["name"], "country": file_record["plant"]["country"]},
                "reporting_period": str(file_record["year"]),
                "process_route": ["EAF", "continuous_casting", "hot_rolling"],
                "claims": {
                    "direct_emissions_max_kg_per_t": limit,
                    "scrap_share_min_permille": min_share,
                    "proof": "groth16",
                    "emissions_commitment": str(emissions_comm),
                    "scrap_commitment": str(scrap_comm),
                },
                "chain": {
                    "network": "sepolia",
                    "registry": get_registry_address(),
                    "file_key": file_key,
                    "attempt_index": i,
                    "docs_root": attempt["docs_root"],
                    "result_hash": attempt["result_hash"],
                    "model_hash": attempt["attestation"]["modelHash"],
                    "ruleset_hash": attempt["attestation"]["rulesetHash"],
                },
            },
        }
        private = {
            "emissions_val": emissions_val,
            "scrap_val": scrap_val,
            "emissions_salt": str(emissions_salt),
            "scrap_salt": str(scrap_salt),
            "emissions_commitment": str(emissions_comm),
            "scrap_commitment": str(scrap_comm),
            "limit": limit,
            "min_share": min_share,
            "vc": vc,
        }
        store._write_json(path, private)

    msg = {
        "fileKey": file_key,
        "attemptIndex": i,
        "docsRoot": attempt["docs_root"],
        "resultHash": attempt["result_hash"],
        "resolutionsHash": compute_resolutions_hash(resolutions),
        "redResolved": len(resolutions.get("red", {})),
        "yellowChecked": len(resolutions.get("yellow_checked", [])),
        "emissionsCommitment": int(private["emissions_commitment"]),
        "scrapCommitment": int(private["scrap_commitment"]),
        "emissionsLimit": private["limit"],
        "minScrapShare": private["min_share"],
        "vcHash": compute_vc_hash(private["vc"]),
    }
    return {"attempt": attempt, "file_record": file_record, "private": private, "msg": msg}


@app.get("/api/files/{file_key}/attempts/{i}/typed-data")
def get_verifier_typed_data(file_key: str, i: int):
    prep = _prepare_verification(file_key, i)
    return get_typed_data_payload("Verification", prep["msg"])


@app.post("/api/files/{file_key}/attempts/{i}/verify")
def verify_and_issue_passport(file_key: str, i: int, req: VerifyRequest):
    prep = _prepare_verification(file_key, i)
    attempt, file_record, private, msg = prep["attempt"], prep["file_record"], prep["private"], prep["msg"]
    counts = attempt.get("counts", {})

    # Same gates as the contract, checked first so the verifier gets a clear message.
    if attempt.get("status") == "missing" or counts.get("missing", 0) > 0:
        raise HTTPException(status_code=400, detail="Signing blocked: evidence is missing")
    if msg["redResolved"] < counts.get("red", 0):
        raise HTTPException(status_code=400, detail=f"Signing blocked: {msg['redResolved']}/{counts.get('red', 0)} red flags resolved")
    if msg["yellowChecked"] < counts.get("yellow", 0):
        raise HTTPException(status_code=400, detail=f"Signing blocked: {msg['yellowChecked']}/{counts.get('yellow', 0)} yellow flags checked")
    if i != len(store.list_attempts(file_key)) - 1:
        raise HTTPException(status_code=400, detail="Signing blocked: only the latest attempt can be signed")

    try:
        _, _, em_proof = generate_proof("emissions_le_limit", {
            "value": str(private["emissions_val"]), "salt": private["emissions_salt"],
            "commitment": private["emissions_commitment"], "limit": str(private["limit"]),
        })
        _, _, sc_proof = generate_proof("scrap_share_ge", {
            "scrapShare": str(private["scrap_val"]), "salt": private["scrap_salt"],
            "commitment": private["scrap_commitment"], "minShare": str(private["min_share"]),
        })
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"Signing blocked: {e}")

    if req.signature:
        verifier_sig = req.signature
        verifier_addr = recover_typed_signer("Verification", msg, req.signature)
    elif req.demo_signer:
        verifier_addr, verifier_sig = sign_verification(msg)
    else:
        raise HTTPException(status_code=400, detail="A verifier signature (or demo_signer) is required")

    tx_hash = None
    if is_offline():
        passport_id = len(store.list_passports()) + 1
    else:
        try:
            sent = onchain.issue_passport(
                file_key, i, [e["doc_sha256"] for e in attempt["extractions"]], msg, verifier_sig, em_proof, sc_proof
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Sepolia issuePassport failed: {e}")
        passport_id, tx_hash = sent["passport_id"], sent["tx_hash"]

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    on_chain = tx_hash is not None
    passport_data = {
        "passport_id": passport_id,
        "file_key": file_key,
        "attempt_index": i,
        "status": "active",
        "product": file_record["product"],
        "plant": file_record["plant"],
        "reporting_period": str(file_record["year"]),
        "verified_by": {"name": "Demo Verification GmbH (fictional)", "address": verifier_addr},
        "issued_at": now_iso,
        "process_route": ["EAF", "continuous_casting", "hot_rolling"],
        "claims": [
            {"label": "Direct emissions", "statement": f"≤ {private['limit'] / 1000:.3f} tCO₂ per tonne",
             "proof": "zk-groth16", "verified_on_chain": on_chain},
            {"label": "Scrap share of metal input", "statement": f"≥ {private['min_share'] / 10:g}%",
             "proof": "zk-groth16", "verified_on_chain": on_chain},
        ],
        "eu_default_value_t_per_t": 2.310,
        "markup_2026": 0.10,
        "documents_unchanged": True,
        "attempt_count": len(store.list_attempts(file_key)),
        "model": attempt["model"],
        "ruleset_version": attempt.get("ruleset", {}).get("version", ""),
        "chain": {
            "registry": get_registry_address() or None,
            "tx_hash": tx_hash,
            "etherscan": f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None,
        },
        "vc_url": f"/api/passports/{passport_id}/vc",
    }
    store.save_passport(passport_id, passport_data)

    file_record["state"] = "verified"
    file_record["passport_id"] = passport_id
    file_record["updated_at"] = now_iso
    store.save_file(file_record)

    return {
        "passport_id": passport_id,
        "tx_hash": tx_hash,
        "etherscan": passport_data["chain"]["etherscan"],
        # Handed to the exporter only, to pass privately to its EU importer.
        "importer_salt": private["emissions_salt"],
    }


@app.get("/api/files/{file_key}/importer-salt")
def get_importer_salt(file_key: str):
    """Exporter view: the salt that opens the emissions commitment of this file's passport.

    The exporter passes it privately to its EU importer. Demo only: there is no login, so this
    endpoint stands for the exporter's own account.
    """
    file_record = store.get_file(file_key)
    passport = store.get_passport(file_record["passport_id"]) if file_record and file_record.get("passport_id") else None
    private = store._read_json(_private_path(file_key, passport["attempt_index"])) if passport else None
    if not private:
        raise HTTPException(status_code=404, detail="No passport with a disclosure salt for this file yet")
    return {"passport_id": passport["passport_id"], "importer_salt": private["emissions_salt"]}


@app.get("/api/passports/{id}")
def get_passport_public(id: int):
    p = store.get_passport(id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Passport #{id} not found")
    return p


@app.get("/api/passports/{id}/disclose")
def disclose_passport(id: int, salts: Optional[str] = Query(None)):
    """Importer view: the exact emissions value, only for whoever holds the salt (spec section 8)."""
    p = store.get_passport(id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Passport #{id} not found")
    private = store._read_json(_private_path(p["file_key"], p["attempt_index"])) or {}
    salt = (salts or "").split(",")[0].strip()
    if not salt or not salt.isdigit():
        raise HTTPException(status_code=403, detail="The exporter's disclosure salt is required")
    on_chain_commitment = private.get("emissions_commitment")
    if not is_offline():
        on_chain_commitment = str(onchain.registry().functions.getPassport(id).call()[7])
    value = private.get("emissions_val")
    if value is None or str(compute_poseidon_commitment(value, int(salt))) != str(on_chain_commitment):
        raise HTTPException(status_code=403, detail="Salt does not open the sealed commitment")
    return {
        "passport_id": id,
        "direct_kg_per_t": value,
        "commitment_match": True,
        "cost_gap_note": "Using the verified value instead of the EU default (2.310 tCO2/t + 10% mark-up in 2026).",
    }


@app.get("/api/passports/{id}/vc")
def get_passport_vc(id: int):
    p = store.get_passport(id)
    if not p:
        raise HTTPException(status_code=404, detail="VC not found")
    private = store._read_json(_private_path(p["file_key"], p["attempt_index"])) or {}
    if "vc" not in private:
        raise HTTPException(status_code=404, detail="VC not found")
    return private["vc"]


@app.get("/api/docs/{file_key}/{i}/{doc_id}")
def serve_doc_pdf(file_key: str, i: int, doc_id: str):
    attempt = store.get_attempt(file_key, i)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    candidate = get_project_root() / "data" / "cases" / attempt.get("case_id", "") / "docs" / f"{doc_id}.pdf"
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(candidate, media_type="application/pdf")


# GS1 Digital Link resolver (spec section 9): the newest active passport for the GTIN + lot.
@app.get("/01/{gtin}/10/{lot}")
def gs1_digital_link(gtin: str, lot: str):
    matches = [
        p for p in store.list_passports()
        if p.get("product", {}).get("gtin") == gtin and p.get("product", {}).get("lot") == lot and p.get("status") == "active"
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="No active passport for this GTIN and lot")
    newest = max(matches, key=lambda p: p["passport_id"])
    return RedirectResponse(url=f"/passport/{newest['passport_id']}", status_code=307)


# Serve frontend web/dist if built (SPA fallback)
web_dist = get_project_root() / "web" / "dist"
if web_dist.exists() and (web_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # The scroll landing page is the home page
        landing = web_dist / "landing" / "index.html"
        if full_path in ("", "landing", "landing/") and landing.exists():
            return FileResponse(landing)
        # If static file exists, return it
        target = web_dist / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        # Otherwise fallback to index.html
        return FileResponse(web_dist / "index.html")
