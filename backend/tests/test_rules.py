import pytest
from damga.rules import evaluate_rules
from damga.sector import load_sector_pack


@pytest.fixture
def sector_data():
    data, _ = load_sector_pack()
    return data


def test_rule_form_vs_docs_red(sector_data):
    # Form says 0 t pig iron, docs show 800 t
    form = {
        "inputs": {"scrap_t": 272000.0, "pig_iron_t": 0.0},
        "production": {"crude_steel_t": 250000.0, "product_t": 240000.0},
    }
    docs = {
        "scrap_t": 272000.0,
        "pig_iron_t": 800.0,
        "crude_steel_t": 250000.0,
        "product_t": 240000.0,
    }
    extractions = [
        {"doc_id": "INV-PIG-012", "doc_type": "purchase_invoice", "fields": [{"key": "pig_iron_t", "value": 800.0, "quote": "Pig iron 800 t", "quote_check": "pass"}]}
    ]
    manifest = [
        {"type": "gas_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "electricity_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "purchase_invoice", "period": "2026"},
        {"type": "lab_analysis", "period": "2026"},
        {"type": "production_record", "period": "2026"},
        {"type": "process_flow", "period": "2026"},
    ]
    emissions = {"direct_kg_per_t": 92}

    flags, counts, status = evaluate_rules(form, docs, extractions, emissions, manifest, sector_data)
    rules_triggered = [f["rule"] for f in flags]

    assert "form_vs_docs" in rules_triggered
    red_flags = [f for f in flags if f["level"] == "red"]
    assert len(red_flags) >= 1
    assert counts["red"] >= 1
    assert status == "red"


def test_rule_material_balance_red(sector_data):
    # Metal input: 100,000 t, crude steel produced: 150,000 t (yield 1.5 > max 0.95)
    form = {
        "inputs": {"scrap_t": 100000.0},
        "production": {"crude_steel_t": 150000.0},
    }
    docs = {
        "scrap_t": 100000.0,
        "crude_steel_t": 150000.0,
    }
    manifest = [
        {"type": "gas_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "electricity_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "purchase_invoice", "period": "2026"},
        {"type": "lab_analysis", "period": "2026"},
        {"type": "production_record", "period": "2026"},
        {"type": "process_flow", "period": "2026"},
    ]
    emissions = {"direct_kg_per_t": 90}

    flags, counts, status = evaluate_rules(form, docs, [], emissions, manifest, sector_data)
    rules_triggered = [f["rule"] for f in flags]
    assert "material_balance" in rules_triggered
    assert status == "red"


def test_rule_missing_evidence(sector_data):
    # Only 10 gas bills instead of 12
    form = {"inputs": {}, "production": {"crude_steel_t": 250000.0}}
    docs = {"crude_steel_t": 250000.0}
    manifest = [{"type": "gas_bill", "period": f"2026-{m:02d}"} for m in range(1, 11)]  # only 10
    emissions = {"direct_kg_per_t": 90}

    flags, counts, status = evaluate_rules(form, docs, [], emissions, manifest, sector_data)
    rules_triggered = [f["rule"] for f in flags]
    assert "missing_evidence" in rules_triggered
    assert counts["missing"] >= 1
    assert status == "missing"


def test_rule_quote_check_missing(sector_data):
    extractions = [
        {"doc_id": "INV-1", "fields": [{"key": "scrap_t", "value": 500.0, "quote": "...", "quote_check": "fail"}]}
    ]
    form = {"inputs": {}, "production": {}}
    docs = {}
    manifest = []
    emissions = {"direct_kg_per_t": 90}

    flags, counts, status = evaluate_rules(form, docs, extractions, emissions, manifest, sector_data)
    rules_triggered = [f["rule"] for f in flags]
    assert "quote_check" in rules_triggered
    assert counts["missing"] >= 1


def test_rule_sector_range_yellow(sector_data):
    # Electricity consumption: 800 kWh/t (above BREF max 600 kWh/t)
    form = {
        "production": {"crude_steel_t": 100000.0},
        "electricity_mwh": 80000.0,  # 80000 MWh / 100000 t = 800 kWh/t
    }
    docs = {
        "crude_steel_t": 100000.0,
        "electricity_mwh": 80000.0,
    }
    manifest = [
        {"type": "gas_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "electricity_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "purchase_invoice", "period": "2026"},
        {"type": "lab_analysis", "period": "2026"},
        {"type": "production_record", "period": "2026"},
        {"type": "process_flow", "period": "2026"},
    ]
    emissions = {"direct_kg_per_t": 90}

    flags, counts, status = evaluate_rules(form, docs, [], emissions, manifest, sector_data)
    rules_triggered = [f["rule"] for f in flags]
    assert "sector_range_electricity" in rules_triggered
    assert counts["yellow"] >= 1
    assert status == "yellow"


def test_rule_low_vs_sector_yellow(sector_data):
    # Direct emissions: 20 kgCO2/t (below min 45)
    form = {"production": {"crude_steel_t": 100000.0}}
    docs = {"crude_steel_t": 100000.0}
    manifest = [
        {"type": "gas_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "electricity_bill", "period": f"2026-{m:02d}"} for m in range(1, 13)
    ] + [
        {"type": "purchase_invoice", "period": "2026"},
        {"type": "lab_analysis", "period": "2026"},
        {"type": "production_record", "period": "2026"},
        {"type": "process_flow", "period": "2026"},
    ]
    emissions = {"direct_kg_per_t": 20}  # below min 45

    flags, counts, status = evaluate_rules(form, docs, [], emissions, manifest, sector_data)
    rules_triggered = [f["rule"] for f in flags]
    assert "low_vs_sector" in rules_triggered
    assert status == "yellow"


def test_status_escalation_order(sector_data):
    # Missing trumps Red; Red trumps Yellow; Yellow trumps Green
    form = {
        "inputs": {"scrap_t": 1000.0, "pig_iron_t": 0.0},  # form_vs_docs will be RED
        "production": {"crude_steel_t": 100000.0},
    }
    docs = {
        "scrap_t": 1000.0,
        "pig_iron_t": 500.0,  # RED
        "crude_steel_t": 100000.0,
    }
    # Manifest missing gas bills -> MISSING
    manifest = []
    emissions = {"direct_kg_per_t": 20}  # YELLOW

    flags, counts, status = evaluate_rules(form, docs, [], emissions, manifest, sector_data)
    assert counts["missing"] > 0
    assert counts["red"] > 0
    assert counts["yellow"] > 0
    # Worst status wins: missing > red > yellow > green
    assert status == "missing"
