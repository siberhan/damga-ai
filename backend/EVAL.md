# Damga AI Pipeline Evaluation Report

- **Total Cases Evaluated**: 42
- **Status Accuracy**: 100.0% (42/42)

## Confusion Matrix (Rows = Expected, Columns = Actual)

| Expected \ Actual | Green | Yellow | Red | Missing |
|---|---|---|---|---|
| **GREEN** | 19 | 0 | 0 | 0 |
| **YELLOW** | 0 | 2 | 0 | 0 |
| **RED** | 0 | 0 | 18 | 0 |
| **MISSING** | 0 | 0 | 0 | 3 |

## Rule Detection Performance

| Rule ID | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| `form_vs_docs` | 16 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `injection_screened` | 1 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `material_balance` | 5 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `missing_evidence` | 3 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| `sector_range_electricity` | 2 | 0 | 0 | 100.0% | 100.0% | 100.0% |

## Case Details

| Case ID | Expected Status | Actual Status | Expected Flags | Actual Flags | Status Match |
|---|---|---|---|---|---|
| `cheat-gas-underdeclared-01` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `cheat-pigiron-invoice-01` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `cheat-pigiron-invoice-01-a2` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `cheat-pigiron-invoice-01-a3` | `green` | `green` | - | - | PASS |
| `cheat-pigiron-omitted-01` | `red` | `red` | material_balance | material_balance | PASS |
| `gen-cheat-01` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-02` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-03` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-04` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-05` | `red` | `red` | material_balance | material_balance | PASS |
| `gen-cheat-06` | `red` | `red` | material_balance | material_balance | PASS |
| `gen-cheat-07` | `red` | `red` | material_balance | material_balance | PASS |
| `gen-cheat-08` | `red` | `red` | material_balance | material_balance | PASS |
| `gen-cheat-09` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-10` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-11` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-12` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-13` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-14` | `red` | `red` | form_vs_docs | form_vs_docs | PASS |
| `gen-cheat-15` | `missing` | `missing` | form_vs_docs, missing_evidence | form_vs_docs, missing_evidence | PASS |
| `gen-cheat-16` | `missing` | `missing` | form_vs_docs, missing_evidence, sector_range_electricity | form_vs_docs, missing_evidence, sector_range_electricity | PASS |
| `gen-honest-01` | `green` | `green` | - | - | PASS |
| `gen-honest-02` | `green` | `green` | - | - | PASS |
| `gen-honest-03` | `green` | `green` | - | - | PASS |
| `gen-honest-04` | `green` | `green` | - | - | PASS |
| `gen-honest-05` | `green` | `green` | - | - | PASS |
| `gen-honest-06` | `green` | `green` | - | - | PASS |
| `gen-honest-07` | `green` | `green` | - | - | PASS |
| `gen-honest-08` | `green` | `green` | - | - | PASS |
| `gen-honest-09` | `green` | `green` | - | - | PASS |
| `gen-honest-10` | `green` | `green` | - | - | PASS |
| `gen-honest-11` | `green` | `green` | - | - | PASS |
| `gen-honest-12` | `green` | `green` | - | - | PASS |
| `gen-honest-13` | `green` | `green` | - | - | PASS |
| `gen-honest-14` | `green` | `green` | - | - | PASS |
| `gen-honest-15` | `green` | `green` | - | - | PASS |
| `gen-honest-16` | `green` | `green` | - | - | PASS |
| `honest-01` | `green` | `green` | - | - | PASS |
| `injection-01` | `yellow` | `yellow` | injection_screened | injection_screened | PASS |
| `missing-gas-01` | `missing` | `missing` | form_vs_docs, missing_evidence | form_vs_docs, missing_evidence | PASS |
| `tamper-01` | `green` | `green` | - | - | PASS |
| `yellow-low-electricity-01` | `yellow` | `yellow` | sector_range_electricity | sector_range_electricity | PASS |
