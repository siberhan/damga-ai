from typing import Any, Dict, List


def calculate_emissions(totals: Dict[str, float], sector_data: Dict[str, Any], precursors_list: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """
    Calculates CBAM direct emissions and scrap share per spec section 6.
    Deterministic, factors taken from sector pack.
    """
    factors = sector_data.get("factors", {})

    # 1. Natural gas fuel emissions
    gas_factors = factors.get("natural_gas", {})
    ncv = gas_factors.get("ncv", {}).get("value", 35.8)  # GJ / 1000 m3
    ef = gas_factors.get("ef", {}).get("value", 56.1)    # tCO2 / TJ
    gas_m3 = totals.get("natural_gas_m3", 0.0)

    # (m3 / 1000) * ncv gives GJ. GJ / 1000 gives TJ. TJ * ef gives tCO2.
    fuel_co2_t = (gas_m3 * ncv * ef) / 1_000_000.0

    # 2. Carbon balance: (inputs C - outputs C) * 44/12
    c_factors = factors.get("carbon_content", {})
    c_electrodes = c_factors.get("electrodes", {}).get("value", 0.99)
    c_carbon_charge = c_factors.get("carbon_charge", {}).get("value", 0.85)
    c_pig_iron = totals.get("c_content_pig_iron", c_factors.get("pig_iron", {}).get("value", 0.04))
    c_dri = totals.get("c_content_dri", c_factors.get("dri", {}).get("value", 0.02))
    c_scrap = totals.get("c_content_scrap", c_factors.get("scrap", {}).get("value", 0.005))
    c_ferroalloys = c_factors.get("ferroalloys", {}).get("value", 0.07)

    c_product = totals.get("c_content_product", c_factors.get("product", {}).get("value", 0.002))
    c_slag = totals.get("c_content_slag", c_factors.get("slag", {}).get("value", 0.000))

    c_in = (
        totals.get("electrodes_t", 0.0) * c_electrodes
        + totals.get("carbon_charge_t", 0.0) * c_carbon_charge
        + totals.get("pig_iron_t", 0.0) * c_pig_iron
        + totals.get("dri_t", 0.0) * c_dri
        + totals.get("scrap_t", 0.0) * c_scrap
        + totals.get("ferroalloys_t", 0.0) * c_ferroalloys
    )

    product_t = totals.get("product_t", 0.0)
    # If product_t is not in doc extractions, fallback to crude_steel_t or billet_t
    if product_t <= 0:
        product_t = totals.get("billet_t", totals.get("crude_steel_t", 1.0))

    c_out = (
        product_t * c_product
        + totals.get("slag_t", 0.0) * c_slag
    )

    delta_c = max(0.0, c_in - c_out)
    carbon_co2_t = delta_c * (44.0 / 12.0)

    # 3. Precursors emissions
    precursor_defaults = factors.get("precursor_default_t_per_t", {})
    pig_default = precursor_defaults.get("pig_iron", {}).get("value", 1.85)
    dri_default = precursor_defaults.get("dri", {}).get("value", 0.70)

    # If precursors list provided with explicit embedded emissions, use those
    precursor_co2_t = 0.0
    if precursors_list:
        for p in precursors_list:
            tonnes = float(p.get("tonnes", 0.0))
            embedded = float(p.get("embedded_emissions_t_per_t", 0.0))
            precursor_co2_t += tonnes * embedded
    else:
        # Precursor emissions from purchased pig iron & dri if any (or 0 if counted as direct only)
        # Per spec section 6: precursor_t = Σ purchased precursor tonnes × its embedded emissions
        # If no explicit precursor list, check if pig_iron or dri have embedded precursor factors
        pass

    # Total direct emissions
    total_co2_t = fuel_co2_t + carbon_co2_t + precursor_co2_t
    direct_kg_per_t = round(1000.0 * total_co2_t / max(product_t, 1e-6))

    # Scrap share and input mix
    scrap_t = totals.get("scrap_t", 0.0)
    pig_iron_t = totals.get("pig_iron_t", 0.0)
    dri_t = totals.get("dri_t", 0.0)
    metal_total = scrap_t + pig_iron_t + dri_t

    if metal_total > 0:
        scrap_share_permille = round(1000.0 * scrap_t / metal_total)
        pig_iron_permille = round(1000.0 * pig_iron_t / metal_total)
        dri_permille = round(1000.0 * dri_t / metal_total)
        # Ensure sum is 1000
        remainder = 1000 - (scrap_share_permille + pig_iron_permille + dri_permille)
        scrap_share_permille += remainder
    else:
        scrap_share_permille = 1000
        pig_iron_permille = 0
        dri_permille = 0

    return {
        "direct_kg_per_t": int(direct_kg_per_t),
        "breakdown": [
            {"source": "natural_gas", "t_co2": round(fuel_co2_t, 1)},
            {"source": "carbon_inputs_minus_outputs", "t_co2": round(carbon_co2_t, 1)},
            {"source": "precursors", "t_co2": round(precursor_co2_t, 1)},
        ],
        "scrap_share_permille": int(scrap_share_permille),
        "input_mix_permille": {
            "scrap": int(scrap_share_permille),
            "pig_iron": int(pig_iron_permille),
            "dri": int(dri_permille),
        },
    }
