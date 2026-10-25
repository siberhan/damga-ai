# Damga AI — Synthetic Dataset & Sector Data Pack

"The numbers are real EU data and real sector ranges. The invoices are synthetic."

## 1. Overview

Real plant invoices, scrap delivery receipts, and utility bills are proprietary commercial trade secrets. To demonstrate and benchmark the Damga AI system without exposing confidential industrial data, this directory provides a deterministic, synthetically generated set of industrial evidence documents and CBAM declarations.

Every number range, standard conversion factor, default precursor intensity, and regulatory threshold is grounded in official European Commission legislation and the EU Best Available Techniques Reference Document (BREF) for Iron and Steel Production. The invoices, bills, and tickets are synthetic text-based PDFs generated deterministically using `fpdf2`.

---

## 2. Sector Pack (`sectors/steel_eaf.yaml`)

The sector configuration defines standard reporting parameters, default emission factors, document types, valid ranges, and automated validation rules for scrap-based Electric Arc Furnace (EAF) steel production (CN 72142000, Rebar).

### 2.1 Fixed Official CBAM Constants
- **EU Default Specific Embedded Emissions (Türkiye, CN 72142000)**: `2.310 tCO2e/t`
  - *Source*: Commission Implementing Regulation (EU) 2026/1740 Annex I / (EU) 2025/2621 Annex I.
- **2026 Regulatory Mark-up**: `0.10` (+10% statutory penalty for using default values).
- **EU ETS Benchmark Intensities**:
  - `bf_bof`: `1.364 tCO2e/t` (Blast Furnace / Basic Oxygen Furnace primary route)
  - `scrap_eaf`: `0.066 tCO2e/t` (Scrap-based Electric Arc Furnace benchmark)
  - *Source*: Commission Implementing Regulation (EU) 2025/2620.

### 2.2 Standard Physical & Emission Factors
- **Natural Gas Net Calorific Value (NCV)**: `34.8 GJ/1000m3` (equivalent to `34.8 MJ/m3` for standard G20 European natural gas).
  - *Source*: Commission Implementing Regulation (EU) 2018/2066 Annex VI / EN 437 G20 standard natural gas Net Calorific Value.
- **Natural Gas Emission Factor (EF)**: `56.1 tCO2/TJ` (`56.1 kgCO2/GJ`).
  - *Source*: 2006 IPCC Guidelines for National Greenhouse Gas Inventories, Vol. 2 (Energy), Ch. 1, Table 1.4; Commission Implementing Regulation (EU) 2018/2066 Annex VI Table 1; Commission Implementing Regulation (EU) 2025/2547.
- **Carbon Content Factors (tC/t)**:
  - **Graphite Electrodes**: `0.82 tC/t`
    - *Source*: 2006 IPCC Guidelines, Vol. 3 (IPPU), Ch. 4 (Metal Industry Emissions), Table 4.3 (EAF Carbon Electrodes).
  - **Anthracite / Carbon Charge**: `0.83 tC/t`
    - *Source*: 2006 IPCC Guidelines, Vol. 3 (IPPU), Ch. 4, Table 4.3 (EAF Charge Carbon / Anthracite / Coke).
  - **Pig Iron**: `0.04 tC/t` (4.0% C)
    - *Source*: 2006 IPCC Guidelines, Vol. 3 (IPPU), Ch. 4, Table 4.3 (Pig Iron).
  - **Direct Reduced Iron (DRI)**: `0.02 tC/t` (2.0% C)
    - *Source*: 2006 IPCC Guidelines, Vol. 3 (IPPU), Ch. 4, Table 4.3 (Direct Reduced Iron).
  - **Scrap**: `0.005 tC/t` (0.50% C)
    - *Source*: 2006 IPCC Guidelines, Vol. 3 (IPPU), Ch. 4, Table 4.3 / Typical low-alloy carbon steel scrap (0.2–0.5% C).
  - **Steel Product (Rebar B500B)**: `0.002 tC/t` (0.20% C)
    - *Source*: 2006 IPCC Guidelines, Vol. 3 (IPPU), Ch. 4, Table 4.3 / Rebar carbon content specification.
  - **EAF Slag**: `0.001 tC/t` (0.10% C)
    - *Source*: Iron and steel EAF metallurgical slag operational residual carbon content.
  - **Ferroalloys (FeMn / SiMn)**: `0.07 tC/t`
    - *Source*: EU ETS Monitoring and Reporting Regulation standard default for bulk ferro-alloys.
- **Precursor Embedded Emissions Defaults for Türkiye**:
  - **Pig Iron (CN 7201)**: `1.85 tCO2e/t`
    - *Source*: Implementing Regulation (EU) 2026/1740 Annex I / (EU) 2025/2621 Annex I for Türkiye.
  - **DRI (CN 7203)**: `null` (not listed for Türkiye in Annex I; generic fallback applies).

### 2.3 Sector Benchmark Ranges (Iron & Steel BREF)
All operational ranges are taken from the European IPPC Bureau (EIPPCB) Best Available Techniques (BAT) Reference Document for Iron and Steel Production (Remus et al., 2013, EUR 25521 EN, Table 8.1, p. 429) and Ferrous Metals Processing (FMP) BREF (2022, EUR 31321 EN, Table 2.6):
- **Liquid Steel Yield per Metallic Input (`yield_liquid_per_metal_input`)**: `[0.812, 0.963]` (Table 8.1: metallic charge 1,039 to 1,232 kg scrap/t liquid steel).
- **Electricity Consumption (`electricity_kwh_per_t`)**: `[404.0, 748.0] kWh/t LS` (Table 8.1: EAF electricity consumption).
- **Natural Gas Consumption (`natural_gas_m3_per_t`)**: `[1.39, 50.0] m3/t LS` (Table 8.1: EAF oxy-fuel burners 50–1500 MJ/t plus FMP Table 2.6 reheating furnace).
- **Graphite Electrodes (`electrodes_kg_per_t`)**: `[2.0, 6.0] kg/t LS` (Table 8.1: Graphite electrodes consumption).
- **Lime / Dolomite Flux (`lime_kg_per_t`)**: `[25.0, 140.0] kg/t LS` (Table 8.1: Lime and dolomite fluxes).
- **Direct CO2 Emissions (`direct_kg_co2_per_t`)**: `[72.0, 180.0] kgCO2/t LS` (Table 8.1: Direct gaseous CO2 emissions from off-gas).

---

## 3. Synthetic Document Set Structure

Every case in `data/cases/<case_id>/` contains:
```
data/cases/<case_id>/
├── declaration.json   # Exporter annual declaration form (CBAM template shape)
├── manifest.json      # List of all evidence documents with raw SHA-256 hashes
├── truth.json         # Ground truth expected status, expected flags, and cheat notes
├── docs/              # Real, generated text-based PDFs (fpdf2)
│   ├── GAS-2026-01.pdf ... GAS-2026-12.pdf       # 12 monthly gas utility bills
│   ├── ELEC-2026-01.pdf ... ELEC-2026-12.pdf     # 12 monthly electricity bills
│   ├── INV-SCRAP-Q1.pdf ... INV-SCRAP-Q4.pdf     # 4 quarterly scrap purchase invoices
│   ├── INV-ELECTRODES-01.pdf                     # Graphite electrodes invoice
│   ├── INV-CARBON-01.pdf                         # Anthracite recarburiser invoice
│   ├── INV-LIME-01.pdf                           # Quicklime flux invoice
│   ├── INV-FERROALLOYS-01.pdf                    # Ferroalloys invoice
│   ├── WB-2026-Q1.pdf                            # Calibrated weighbridge ticket
│   ├── LAB-2026.pdf                              # Accredited OES lab analysis report
│   ├── PROD-2026.pdf                             # Annual melt shop production record
│   └── PFD-2026.pdf                              # Plant process flow & boundary sheet
└── docs_tampered/     # (tamper-01 only) Contains PDF modified post-sealing
```

### Document Design & Realism
- **Fictional Entity Names**:
  - Exporter: `"Aliağa Demo Steel Works (fictional)"`, Plant ID `TR-ALIAGA-DEMO-001`.
  - Utility Suppliers: `"Demo Gaz Dağıtım A.Ş. (fictional)"`, `"Demo Ege Elektrik Dağıtım A.Ş. (fictional)"`.
  - Raw Material Suppliers: `"Demo Scrap Trading Ltd. (fictional)"`, `"Demo Pig Iron Import Trading GmbH (fictional)"`, `"Demo Carbon Materials GmbH (fictional)"`, `"Demo Lime Works Ltd. (fictional)"`, `"Demo Ferro-Alloy BV (fictional)"`.
  - Service Providers: `"Demo Aliağa Kantar ve Tartı Hizmetleri A.Ş. (fictional)"`, `"Demo Spektrometri ve Metalurji Laboratuvarı A.Ş. (fictional)"`.
- **Typographic Diversity & Formatting**:
  - Uses Unicode fonts (macOS `/System/Library/Fonts/Supplemental/Arial.ttf` or `Arial Unicode.ttf`).
  - Alternates between US numerical format (`1,234.5`) and Turkish/European format (`1.234,5`).
  - Prices appear realistically on commercial invoices (e.g. scrap EUR 385/t, electricity EUR 95/MWh), showing that commercial figures remain private while physical and emission quantities are audited.

---

## 4. Test Case Catalog

### 4.1 Named Demo Cases (Video Walkthroughs)
| Case ID | Expected Status | Expected Flags | Description |
|---|---|---|---|
| `honest-01` | `green` | `[]` | Clean scrap EAF plant. Inputs within BREF ranges; form matches sum of docs exactly. |
| `cheat-pigiron-invoice-01` | `red` | `["form_vs_docs"]` | Cheater uploaded an 800 t pig iron invoice, but declared 0 t pig iron on the form. |
| `cheat-pigiron-invoice-01-a2` | `red` | `["form_vs_docs"]` | Cheater lowered scrap on form to compensate, but pig iron is still omitted (0 t) on form. |
| `cheat-pigiron-invoice-01-a3` | `green` | `[]` | Corrected attempt: 800 t pig iron declared on form matching the invoice. |
| `cheat-pigiron-omitted-01` | `red` | `["material_balance"]` | Pig iron was used in production but its invoice omitted. Scrap invoices yield 1.136, exceeding BREF max (0.963). |
| `cheat-gas-underdeclared-01` | `red` | `["form_vs_docs"]` | Form declares 8,000,000 m3 natural gas, 20% lower than the 10,000,000 m3 in the 12 monthly bills. |
| `missing-gas-01` | `missing` | `["form_vs_docs", "missing_evidence"]` | Only 10 of 12 monthly gas bills uploaded (Nov and Dec missing). |
| `yellow-low-electricity-01` | `yellow` | `["sector_range_electricity"]` | Electricity consumption is 390.0 kWh/t, just below sector BREF lower bound (404.0 kWh/t). |
| `injection-01` | `yellow` | `["injection_screened"]` | Honest file with prompt injection text from `data/injection/attacks.jsonl` in small print; screened by pipeline (yellow info flag). |
| `tamper-01` | `green` | `[]` | Post-seal tamper demo: `docs/` is honest-01; `docs_tampered/` has 1 modified PDF showing hash mismatch. |

### 4.2 Precision & Recall Test Set (32 Cases)
- **`gen-honest-01` to `gen-honest-16`**: 16 honest cases scaled across steel mill production volumes from 150,000 t to 350,000 t/year. All per-tonne ratios sit squarely inside EU BREF ranges; form totals equal evidence sums within 0.1%.
- **`gen-cheat-01` to `gen-cheat-04`**: Hidden pig iron with uploaded invoice (`form_vs_docs`, red).
- **`gen-cheat-05` to `gen-cheat-08`**: Hidden pig iron without invoice; insufficient scrap charged (`material_balance`, red).
- **`gen-cheat-09` to `gen-cheat-12`**: Natural gas under-declared on form by 18% to 26% (`form_vs_docs`, red).
- **`gen-cheat-13` to `gen-cheat-14`**: Scrap over-declared on form by 8% (`form_vs_docs`, red).
- **`gen-cheat-15`**: Missing December gas bill (`missing_evidence`, missing).
- **`gen-cheat-16`**: Missing November and December electricity bills (`missing_evidence`, missing).

---

## 5. How to Rebuild and Evaluate

```bash
# 1. Activate venv
source data/.venv/bin/activate

# 2. Rebuild all 42 cases deterministically
data/.venv/bin/python data/generate.py

# 3. Run evaluation across all 42 cases
PYTHONPATH=backend backend/.venv/bin/python backend/damga/eval.py
```

## 6. Known Limits (read before trusting the numbers)

- **The cases are synthetic.** No real plant data is used. Plant values follow the EU Iron & Steel BREF (2013) Table 8.1 ranges, and the EU default values come from Implementing Regulation (EU) 2025/2621 Annex I (Türkiye: CN 7214 20 00 rebar 2.310 tCO2e/t, CN 7201 pig iron 1.850 tCO2e/t).
- **The cheats are clear on purpose.** They are built so that a viewer can see the catch in a short demo. The 16 generated honest cases are one plant at different sizes.
- **Form vs. documents has a 2% tolerance.** Code, not the AI, compares the form with the document totals. Honest files also have small gaps (meter rounding, billing periods), so a gap of 2% or less is accepted. With 10,000,000 m3 of gas in the bills:

  | Form says | Gap | Result |
  |---|---|---|
  | 9,700,000 m3 | 3% lower | red flag |
  | 9,850,000 m3 | 1.5% lower | **not flagged** (inside the tolerance) |

  A 1.5% gas gap hides about 1–2 kg CO2 per tonne of steel.
- **If the documents are also false, only physics checks remain.** When a plant puts the same false number on the form and on the documents, only the material balance (yield) and the BREF ranges can catch it, and these ranges are wide. This is why a signed human verifier stays in the loop: Damga makes the verifier's work faster and traceable, it does not replace the verifier.
