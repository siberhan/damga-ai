from typing import Any, Dict, List, Tuple


def evaluate_rules(
    form_data: Dict[str, Any],
    doc_totals: Dict[str, float],
    extractions: List[Dict[str, Any]],
    emissions: Dict[str, Any],
    manifest_docs: List[Dict[str, Any]],
    sector_data: Dict[str, Any],
    screened_removals: List[Dict[str, Any]] | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int], str]:
    """
    Evaluates all rules from spec section 4 table.
    Returns (flags_list, counts, status).
    """
    flags: List[Dict[str, Any]] = []
    flag_idx = 1

    ranges = sector_data.get("ranges", {})
    rules_config = sector_data.get("rules", {})

    # Helper to add flag
    def add_flag(
        level: str,
        rule: str,
        source: str,
        message: str,
        field: str | None = None,
        values: Dict[str, Any] | None = None,
        evidence: List[Dict[str, Any]] | None = None,
        ai_explanation: str = "",
    ):
        nonlocal flag_idx
        # AI-sourced findings are capped at yellow
        if source == "ai" and level in ("red", "missing"):
            level = "yellow"

        flags.append({
            "id": f"F{flag_idx}",
            "level": level,
            "rule": rule,
            "source": source,
            "field": field,
            "message": message,
            "values": values or {},
            "evidence": evidence or [],
            "ai_explanation": ai_explanation,
            "state": "open",
            "resolution": None,
        })
        flag_idx += 1

    # Flatten form values
    form_inputs = form_data.get("inputs", {})
    form_production = form_data.get("production", {})
    form_fuels = form_data.get("fuels", {})
    form_elec = form_data.get("electricity_mwh", 0.0)

    form_totals: Dict[str, float] = {}
    for k, v in form_inputs.items():
        if isinstance(v, (int, float)):
            form_totals[k] = float(v)
    for k, v in form_production.items():
        if isinstance(v, (int, float)):
            form_totals[k] = float(v)
    for k, v in form_fuels.items():
        if isinstance(v, (int, float)):
            form_totals[k] = float(v)
    if isinstance(form_elec, (int, float)):
        form_totals["electricity_mwh"] = float(form_elec)

    # 1. form_vs_docs rule (red)
    tolerance_pct = float(rules_config.get("form_vs_docs", {}).get("tolerance_pct", 2.0))
    # Only fields the form declares are compared; lab carbon contents feed the math but are not on the form.
    for key in sorted(form_totals):
        form_v = form_totals.get(key, 0.0)
        docs_v = doc_totals.get(key, 0.0)

        # Skip zero/empty on both sides
        if abs(form_v) < 1e-9 and abs(docs_v) < 1e-9:
            continue

        denom = max(abs(form_v), abs(docs_v), 1e-6)
        diff_pct = abs(form_v - docs_v) / denom * 100.0

        if diff_pct > tolerance_pct:
            # Find evidence snippets from extractions
            ev = []
            for ext in extractions:
                for fld in ext.get("fields", []):
                    if fld.get("key") == key:
                        ev.append({
                            "doc_id": ext.get("doc_id", ""),
                            "quote": fld.get("quote", ""),
                        })

            add_flag(
                level="red",
                rule="form_vs_docs",
                source="code",
                field=key,
                message=f"The form says {form_v:g} of {key}, but evidence documents show {docs_v:g}.",
                values={"form": form_v, "docs": docs_v, "tolerance_pct": tolerance_pct},
                evidence=ev,
                ai_explanation=f"A discrepancy of {diff_pct:.1f}% between form declaration and uploaded evidence violates CBAM consistency requirements.",
            )

    # 2. material_balance rule (red)
    scrap_t = doc_totals.get("scrap_t", form_totals.get("scrap_t", 0.0))
    pig_iron_t = doc_totals.get("pig_iron_t", form_totals.get("pig_iron_t", 0.0))
    dri_t = doc_totals.get("dri_t", form_totals.get("dri_t", 0.0))
    crude_steel_t = doc_totals.get("crude_steel_t", form_totals.get("crude_steel_t", 0.0))

    metal_in = scrap_t + pig_iron_t + dri_t
    yield_range = ranges.get("yield_liquid_per_metal_input", {"min": 0.88, "max": 0.95})
    min_yield = yield_range.get("min", 0.88)
    max_yield = yield_range.get("max", 0.95)

    if metal_in > 0 and crude_steel_t > 0:
        actual_yield = crude_steel_t / metal_in
        if actual_yield < min_yield or actual_yield > max_yield:
            add_flag(
                level="red",
                rule="material_balance",
                source="code",
                field="crude_steel_t",
                message=f"Yield {actual_yield:.3f} (crude steel {crude_steel_t:g} t / metal input {metal_in:g} t) is outside BREF range [{min_yield}, {max_yield}].",
                values={"yield": round(actual_yield, 4), "min": min_yield, "max": max_yield},
                ai_explanation="The physical metal yield cannot fall outside standard thermodynamic and operational limits for scrap-based EAF production.",
            )

    # 3. missing_evidence rule (missing)
    doc_types_cfg = sector_data.get("doc_types", {})
    type_counts: Dict[str, int] = {}
    type_periods: Dict[str, set] = {}

    for doc in manifest_docs:
        dtype = doc.get("type", "")
        period = doc.get("period", "")
        type_counts[dtype] = type_counts.get(dtype, 0) + 1
        if dtype not in type_periods:
            type_periods[dtype] = set()
        if period:
            type_periods[dtype].add(period)

    for dtype, cfg in doc_types_cfg.items():
        if not cfg.get("required", False):
            continue
        periods_req = cfg.get("periods", "any")

        if periods_req == "monthly":
            # 12 monthly periods required
            periods_present = len(type_periods.get(dtype, set()))
            if periods_present < 12:
                add_flag(
                    level="missing",
                    rule="missing_evidence",
                    source="code",
                    field=dtype,
                    message=f"Missing monthly evidence for {dtype}: found {periods_present}/12 months.",
                    values={"found": periods_present, "required": 12},
                    ai_explanation="EU CBAM guidelines mandate continuous 12-month monitoring for utility and fuel consumptions.",
                )
        elif periods_req == "yearly":
            if type_counts.get(dtype, 0) < 1:
                add_flag(
                    level="missing",
                    rule="missing_evidence",
                    source="code",
                    field=dtype,
                    message=f"Missing required yearly document: {dtype}.",
                    values={"found": 0, "required": 1},
                    ai_explanation=f"A yearly {dtype} document is required under the sector verification plan.",
                )
        else:
            if type_counts.get(dtype, 0) < 1:
                add_flag(
                    level="missing",
                    rule="missing_evidence",
                    source="code",
                    field=dtype,
                    message=f"Missing required evidence document: {dtype}.",
                    values={"found": 0, "required": 1},
                    ai_explanation=f"No {dtype} documents were provided in the manifest.",
                )

    # 4. quote_check rule (missing)
    # Check if any field failed quote check
    failed_quotes = []
    for ext in extractions:
        for fld in ext.get("fields", []):
            if fld.get("quote_check") == "fail":
                failed_quotes.append({
                    "doc_id": ext.get("doc_id", ""),
                    "field": fld.get("key", ""),
                    "quote": fld.get("quote", ""),
                    "value": fld.get("value", 0.0),
                })

    for fq in failed_quotes:
        add_flag(
            level="missing",
            rule="quote_check",
            source="code",
            field=fq["field"],
            message=f"Extracted quote for {fq['field']} in {fq['doc_id']} could not be verified verbatim against document text.",
            evidence=[{"doc_id": fq["doc_id"], "quote": fq["quote"]}],
            values={"value": fq["value"]},
            ai_explanation="Extracted values must match raw document evidence verbatim to ensure auditability.",
        )

    # 5. sector_range_* rules (yellow)
    ref_prod_t = crude_steel_t if crude_steel_t > 0 else doc_totals.get("product_t", form_totals.get("product_t", 0.0))
    if ref_prod_t > 0:
        # electricity_kwh_per_t
        elec_mwh = doc_totals.get("electricity_mwh", form_totals.get("electricity_mwh", 0.0))
        if elec_mwh > 0:
            elec_kwh_per_t = (elec_mwh * 1000.0) / ref_prod_t
            r_elec = ranges.get("electricity_kwh_per_t", {"min": 380, "max": 600})
            if elec_kwh_per_t < r_elec.get("min", 380) or elec_kwh_per_t > r_elec.get("max", 600):
                add_flag(
                    level="yellow",
                    rule="sector_range_electricity",
                    source="code",
                    field="electricity_mwh",
                    message=f"Electricity consumption of {elec_kwh_per_t:.1f} kWh/t is outside sector BREF range [{r_elec['min']}, {r_elec['max']}].",
                    values={"actual": round(elec_kwh_per_t, 1), "min": r_elec["min"], "max": r_elec["max"]},
                    ai_explanation="Specific electricity consumption outside standard BREF benchmarks requires verifier review.",
                )

        # natural_gas_m3_per_t
        gas_m3 = doc_totals.get("natural_gas_m3", form_totals.get("natural_gas_m3", 0.0))
        if gas_m3 > 0:
            gas_per_t = gas_m3 / ref_prod_t
            r_gas = ranges.get("natural_gas_m3_per_t", {"min": 10, "max": 55})
            if gas_per_t < r_gas.get("min", 10) or gas_per_t > r_gas.get("max", 55):
                add_flag(
                    level="yellow",
                    rule="sector_range_gas",
                    source="code",
                    field="natural_gas_m3",
                    message=f"Natural gas consumption of {gas_per_t:.1f} m3/t is outside sector BREF range [{r_gas['min']}, {r_gas['max']}].",
                    values={"actual": round(gas_per_t, 1), "min": r_gas["min"], "max": r_gas["max"]},
                    ai_explanation="Gas burner efficiency or reheat furnace consumption is outside standard ranges.",
                )

        # electrodes_kg_per_t
        elec_t = doc_totals.get("electrodes_t", form_totals.get("electrodes_t", 0.0))
        if elec_t > 0:
            elec_kg_per_t = (elec_t * 1000.0) / ref_prod_t
            r_elec_t = ranges.get("electrodes_kg_per_t", {"min": 1.0, "max": 2.5})
            if elec_kg_per_t < r_elec_t.get("min", 1.0) or elec_kg_per_t > r_elec_t.get("max", 2.5):
                add_flag(
                    level="yellow",
                    rule="sector_range_electrodes",
                    source="code",
                    field="electrodes_t",
                    message=f"Electrode consumption of {elec_kg_per_t:.2f} kg/t is outside sector BREF range [{r_elec_t['min']}, {r_elec_t['max']}].",
                    values={"actual": round(elec_kg_per_t, 2), "min": r_elec_t["min"], "max": r_elec_t["max"]},
                    ai_explanation="Electrode wear rate is outside normal operating parameters.",
                )

        # lime_kg_per_t
        lime_t = doc_totals.get("lime_t", form_totals.get("lime_t", 0.0))
        if lime_t > 0:
            lime_kg_per_t = (lime_t * 1000.0) / ref_prod_t
            r_lime = ranges.get("lime_kg_per_t", {"min": 25, "max": 65})
            if lime_kg_per_t < r_lime.get("min", 25) or lime_kg_per_t > r_lime.get("max", 65):
                add_flag(
                    level="yellow",
                    rule="sector_range_lime",
                    source="code",
                    field="lime_t",
                    message=f"Lime consumption of {lime_kg_per_t:.1f} kg/t is outside sector BREF range [{r_lime['min']}, {r_lime['max']}].",
                    values={"actual": round(lime_kg_per_t, 1), "min": r_lime["min"], "max": r_lime["max"]},
                    ai_explanation="Slag-forming flux additions deviate from typical operational norms.",
                )

    # 6. low_vs_sector rule (yellow)
    direct_kg = emissions.get("direct_kg_per_t", 0)
    r_direct = ranges.get("direct_kg_co2_per_t", {"min": 45, "max": 250})
    min_direct = r_direct.get("min", 45)
    if direct_kg < min_direct:
        add_flag(
            level="yellow",
            rule="low_vs_sector",
            source="code",
            field="direct_kg_per_t",
            message=f"Direct emissions ({direct_kg} kgCO2/t) are below the sector BREF lower bound ({min_direct} kgCO2/t).",
            values={"actual": direct_kg, "min": min_direct},
            ai_explanation="Direct emissions below the sector minimum require justification from the plant operator.",
        )

    # 7. injection_screened rule (yellow)
    if screened_removals:
        add_flag(
            level="yellow",
            rule="injection_screened",
            source="code",
            message=f"Prompt injection screen removed {len(screened_removals)} suspicious paragraph(s) from document(s).",
            values={"removed_count": len(screened_removals)},
            evidence=[{"doc_id": r.get("doc_id", ""), "quote": r.get("text", "")[:120]} for r in screened_removals],
            ai_explanation="Disallowed instructions found in evidence documents were dropped before model processing.",
        )

    # Compute counts
    red_count = sum(1 for f in flags if f["level"] == "red")
    yellow_count = sum(1 for f in flags if f["level"] == "yellow")
    missing_count = sum(1 for f in flags if f["level"] == "missing")

    counts = {
        "red": red_count,
        "yellow": yellow_count,
        "missing": missing_count,
    }

    # Status: MISSING > RED > YELLOW > GREEN
    if missing_count > 0:
        status = "missing"
    elif red_count > 0:
        status = "red"
    elif yellow_count > 0:
        status = "yellow"
    else:
        status = "green"

    return flags, counts, status
