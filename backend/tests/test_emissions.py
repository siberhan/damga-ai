import pytest
from damga.emissions import calculate_emissions
from damga.sector import load_sector_pack


def test_emissions_deterministic_calculation():
    sector_data, _ = load_sector_pack()

    totals = {
        "scrap_t": 271950.0,
        "pig_iron_t": 800.0,
        "dri_t": 0.0,
        "natural_gas_m3": 11002300.0,
        "electricity_mwh": 104980.0,
        "electrodes_t": 500.0,
        "lime_t": 10010.0,
        "carbon_charge_t": 3000.0,
        "product_t": 240000.0,
        "crude_steel_t": 250000.0,
        "slag_t": 30000.0,
    }

    res1 = calculate_emissions(totals, sector_data)
    res2 = calculate_emissions(totals, sector_data)

    # Determinism
    assert res1 == res2
    assert isinstance(res1["direct_kg_per_t"], int)
    assert res1["direct_kg_per_t"] > 0
    assert res1["scrap_share_permille"] == 997  # 271950 / (271950 + 800) = 0.99706 -> 997
    assert res1["input_mix_permille"]["scrap"] == 997
    assert res1["input_mix_permille"]["pig_iron"] == 3
    assert res1["input_mix_permille"]["dri"] == 0
    assert sum(res1["input_mix_permille"].values()) == 1000

    # Verify breakdown structure
    breakdown = res1["breakdown"]
    sources = [b["source"] for b in breakdown]
    assert "natural_gas" in sources
    assert "carbon_inputs_minus_outputs" in sources
    assert "precursors" in sources


def test_emissions_pure_scrap_case():
    sector_data, _ = load_sector_pack()
    totals = {
        "scrap_t": 100000.0,
        "pig_iron_t": 0.0,
        "dri_t": 0.0,
        "product_t": 90000.0,
        "natural_gas_m3": 2000000.0,
    }
    res = calculate_emissions(totals, sector_data)
    assert res["scrap_share_permille"] == 1000
    assert res["input_mix_permille"]["scrap"] == 1000
    assert res["input_mix_permille"]["pig_iron"] == 0
