import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from damga.chain import sign_ai_attestation
from damga.emissions import calculate_emissions
from damga.extract import extract_fields_from_doc, get_ai_model
from damga.hashing import (
    clean_hex,
    compute_declaration_hash,
    compute_doc_hash,
    compute_docs_root,
    compute_file_key,
    compute_input_hash,
    compute_model_hash,
    compute_plant_id,
    compute_result_hash,
)
from damga.guard import get_guard_model
from damga.injection import screen_text
from damga.pdf_text import extract_text_from_pdf
from damga.quote_check import verify_quote
from damga.rules import evaluate_rules
from damga.sector import load_sector_pack

STATUS_MAP = {"green": 0, "yellow": 1, "red": 2, "missing": 3}
STATUS_REV_MAP = {0: "green", 1: "yellow", 2: "red", 3: "missing"}


def get_project_root() -> Path:
    backend_dir = Path(__file__).resolve().parent.parent
    return backend_dir.parent


def get_precomputed_path(case_id: str, attempt_index: int = 0) -> Path:
    root = get_project_root()
    return root / "data" / "precomputed" / case_id / f"attempt-{attempt_index}.json"


def sum_doc_totals(extractions: List[Dict[str, Any]], doc_types_cfg: Dict[str, Any]) -> Dict[str, float]:
    """Adds up the quote-checked values per field.

    Optional cross-check documents (the weighbridge summary) repeat what the invoices bill,
    so only required document types are summed. A value the model read twice from one
    document (a table row and its total line) counts once.
    """
    totals: Dict[str, float] = {}
    for ext in extractions:
        if not doc_types_cfg.get(ext.get("doc_type", ""), {}).get("required", True):
            continue
        seen = set()
        for fld in ext.get("fields", []):
            item = (fld.get("key"), float(fld.get("value", 0.0)))
            if fld.get("quote_check") == "pass" and item not in seen:
                seen.add(item)
                totals[item[0]] = totals.get(item[0], 0.0) + item[1]
    return totals


def run_pipeline(
    case_dir: Path,
    attempt_index: int = 0,
    live: bool = False,
    sector_pack_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Runs the full AI verification pipeline for a given case folder.
    """
    case_id = case_dir.name
    precomputed_file = get_precomputed_path(case_id, attempt_index)

    # If not live and precomputed result exists, return it
    if not live and precomputed_file.exists():
        data = json.loads(precomputed_file.read_text(encoding="utf-8"))
        return data

    sector_data, ruleset_hash = load_sector_pack(sector_pack_path)
    decl_path = case_dir / "declaration.json"
    manifest_path = case_dir / "manifest.json"

    if not decl_path.exists():
        raise FileNotFoundError(f"declaration.json not found in {case_dir}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {case_dir}")

    declaration = json.loads(decl_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    plant_info = declaration.get("plant", {})
    plant_id_hex = compute_plant_id(plant_info.get("plant_id", "UNKNOWN-PLANT"))
    year = int(declaration.get("year", 2026))
    cn_code = declaration.get("product", {}).get("cn_code", "72142000")
    file_key = compute_file_key(plant_id_hex, year, cn_code)
    declaration_hash = compute_declaration_hash(declaration)

    # Process documents
    doc_entries = manifest.get("documents", [])
    doc_hashes: List[str] = []
    extractions: List[Dict[str, Any]] = []
    all_screened: List[Dict[str, Any]] = []
    doc_types_cfg = sector_data.get("doc_types", {})

    model_name = get_ai_model()
    model_version = os.environ.get("AI_MODEL_VERSION") or "2026-10"
    guard_model = get_guard_model()
    # Both models shape the result, so both are in the approved model hash.
    model_hash = compute_model_hash("openrouter", f"{model_name}+guard:{guard_model}", model_version)

    def process_doc(doc: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        doc_id = doc.get("doc_id", "")
        doc_type = doc.get("type", "")
        rel_file = doc.get("file", f"docs/{doc_id}.pdf")
        doc_path = case_dir / rel_file

        if not doc_path.exists():
            # Check docs/
            doc_path = case_dir / "docs" / f"{doc_id}.pdf"

        if not doc_path.exists():
            raise FileNotFoundError(f"Document PDF not found: {doc_path}")

        pdf_bytes = doc_path.read_bytes()
        doc_sha256 = compute_doc_hash(pdf_bytes)

        # 1. PDF to text
        raw_text = extract_text_from_pdf(pdf_bytes)

        # 2. Injection screen
        screen_res = screen_text(raw_text, use_guard=live)
        kept_text = screen_res["kept_text"]
        removed = screen_res["removed"]

        # 3. Extraction
        allowed_fields = doc_types_cfg.get(doc_type, {}).get("fields", [])
        doc_extraction_fields: List[Dict[str, Any]] = []

        if live:
            extracted = extract_fields_from_doc(doc_id, doc_type, allowed_fields, kept_text, model_name=model_name)
            doc_extraction_fields = extracted.get("fields", [])
        else:
            # In offline/fixture mode if precomputed result is missing, extract basic tokens from text or fixture
            # Fallback heuristic extractor from raw text for offline deterministic tests
            for field_key in allowed_fields:
                import re
                # Simple regex lookup for field values in text
                m = re.search(rf"{field_key}\s*[:=.]+\s*([0-9.,]+)", raw_text, re.IGNORECASE)
                if m:
                    raw_val_str = m.group(1).replace(",", "")
                    try:
                        val = float(raw_val_str)
                        quote = m.group(0)
                        doc_extraction_fields.append({
                            "key": field_key,
                            "value": val,
                            "unit": "t" if "_t" in field_key else ("m3" if "m3" in field_key else "MWh"),
                            "quote": quote,
                            "confidence": 0.95,
                        })
                    except ValueError:
                        pass

        # 4. Quote check
        checked_fields = []
        for fld in doc_extraction_fields:
            quote = fld.get("quote", "")
            val = float(fld.get("value", 0.0))
            passed, qc_status = verify_quote(quote, val, raw_text)
            checked_fields.append({
                **fld,
                "quote_check": qc_status,
            })

        return doc_sha256, {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "period": doc.get("period", ""),
            "doc_sha256": doc_sha256,
            "fields": checked_fields,
            "injection_screen": {"removed": removed, "guard": screen_res["guard"]},
        }

    # Documents are independent, so the model calls run in parallel; results keep manifest order.
    with ThreadPoolExecutor(max_workers=8 if live else 1) as pool:
        for doc_sha256, extraction in pool.map(process_doc, doc_entries):
            doc_hashes.append(doc_sha256)
            extractions.append(extraction)
            all_screened += [{"doc_id": extraction["doc_id"], **r} for r in extraction["injection_screen"]["removed"]]

    docs_root = compute_docs_root(doc_hashes)
    input_hash = compute_input_hash(docs_root, declaration_hash)

    # 5. Aggregate totals from docs (only passing quotes)
    doc_totals = sum_doc_totals(extractions, doc_types_cfg)
    total_conf = 0.0
    conf_count = 0

    for ext in extractions:
        for fld in ext.get("fields", []):
            total_conf += float(fld.get("confidence", 0.95))
            conf_count += 1

    avg_conf = (total_conf / conf_count) if conf_count > 0 else 0.95
    confidence_bps = round(avg_conf * 10000)

    # 6. Emissions math
    emissions = calculate_emissions(doc_totals, sector_data, declaration.get("precursors", []))

    # Form totals for comparison
    form_totals: Dict[str, float] = {}
    for sub in ("inputs", "production", "fuels"):
        for k, v in declaration.get(sub, {}).items():
            if isinstance(v, (int, float)):
                form_totals[k] = float(v)
    if "electricity_mwh" in declaration:
        form_totals["electricity_mwh"] = float(declaration["electricity_mwh"])

    # 7. Evaluate rules
    flags, counts, status = evaluate_rules(
        declaration,
        doc_totals,
        extractions,
        emissions,
        doc_entries,
        sector_data,
        all_screened,
    )

    status_int = STATUS_MAP.get(status, 2)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    attestation: Dict[str, Any] = {
        "fileKey": file_key,
        "inputHash": input_hash,
        "modelHash": model_hash,
        "rulesetHash": ruleset_hash,
        "resultHash": "",  # will be populated
        "status": status_int,
        "redCount": counts["red"],
        "yellowCount": counts["yellow"],
        "missingCount": counts["missing"],
        "confidenceBps": confidence_bps,
    }

    ai_result: Dict[str, Any] = {
        "schema": "damga.ai_result.v1",
        "case_id": case_id,
        "file_key": file_key,
        "attempt_index": attempt_index,
        "docs_root": docs_root,
        "declaration_hash": declaration_hash,
        "input_hash": input_hash,
        "model": {
            "provider": "openrouter",
            "name": model_name,
            "guard_model": guard_model,
            "version": model_version,
            "model_hash": model_hash,
        },
        "ruleset": {
            "id": sector_data.get("id", "steel_eaf"),
            "version": str(sector_data.get("version", "1.0.0")),
            "ruleset_hash": ruleset_hash,
        },
        "extractions": extractions,
        "totals": {
            "from_docs": doc_totals,
            "from_form": form_totals,
        },
        "emissions": emissions,
        "flags": flags,
        "counts": counts,
        "status": status,
        "confidence_bps": confidence_bps,
        "created_at": created_at,
        "result_hash": "",
        "attestation": attestation,
    }

    # Compute resultHash (canonical JSON without signature)
    result_hash = compute_result_hash(ai_result)
    ai_result["result_hash"] = result_hash
    ai_result["attestation"]["resultHash"] = result_hash

    # Sign EIP-712 AIAttestation
    signer_addr, sig = sign_ai_attestation(ai_result["attestation"])
    ai_result["signature"] = {
        "signer": signer_addr,
        "sig": sig,
    }

    return ai_result


def replay_pipeline(
    stored_result: Dict[str, Any],
    declaration: Dict[str, Any],
    sector_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministic replay mode:
    Skips the model and recomputes everything after extraction from stored extractions.
    Returns the replayed ai_result.
    """
    extractions = stored_result.get("extractions", [])
    doc_totals = sum_doc_totals(extractions, sector_data.get("doc_types", {}))
    screened_removals: List[Dict[str, Any]] = []

    for ext in extractions:
        doc_id = ext.get("doc_id", "")
        for rem in ext.get("injection_screen", {}).get("removed", []):
            screened_removals.append({"doc_id": doc_id, **rem})

    emissions = calculate_emissions(doc_totals, sector_data, declaration.get("precursors", []))

    manifest_docs = [
        {"type": ext.get("doc_type", ""), "period": ext.get("period", ""), "doc_id": ext.get("doc_id", "")}
        for ext in extractions
    ]

    flags, counts, status = evaluate_rules(
        declaration,
        doc_totals,
        extractions,
        emissions,
        manifest_docs,
        sector_data,
        screened_removals,
    )

    import copy
    replayed = copy.deepcopy(stored_result)
    replayed["totals"]["from_docs"] = doc_totals
    replayed["emissions"] = emissions
    replayed["flags"] = flags
    replayed["counts"] = counts
    replayed["status"] = status

    # Recompute resultHash
    recomputed_hash = compute_result_hash(replayed)
    replayed["result_hash"] = recomputed_hash
    replayed["attestation"]["resultHash"] = recomputed_hash

    return replayed


def main():
    parser = argparse.ArgumentParser(description="Damga AI Pipeline CLI")
    parser.add_argument("--case", required=True, help="Case ID under data/cases/")
    parser.add_argument("--attempt", type=int, default=0, help="Attempt index (default 0)")
    parser.add_argument("--live", action="store_true", help="Call live Mistral API")
    args = parser.parse_args()

    root = get_project_root()
    case_dir = root / "data" / "cases" / args.case

    if not case_dir.exists():
        print(f"Error: Case directory not found: {case_dir}")
        exit(1)

    result = run_pipeline(case_dir, attempt_index=args.attempt, live=args.live)

    out_file = root / "data" / "precomputed" / args.case / f"attempt-{args.attempt}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Pipeline executed successfully. Result written to {out_file}")
    print(f"Status: {result['status']}, Flags: {result['counts']}, ResultHash: {result['result_hash']}")


if __name__ == "__main__":
    main()
