import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
from damga.pipeline import get_project_root, run_pipeline


def run_evaluation(live: bool = False) -> Dict[str, Any]:
    root = get_project_root()
    cases_dir = root / "data" / "cases"
    eval_md_path = root / "backend" / "EVAL.md"

    if not cases_dir.exists() or not any(cases_dir.iterdir()):
        msg = "No test cases found in data/cases/. The data agent is generating them."
        print(msg)
        eval_md_content = f"# Damga AI Pipeline Evaluation\n\n{msg}\n"
        eval_md_path.write_text(eval_md_content, encoding="utf-8")
        return {"status": "skipped", "message": msg}

    case_dirs = [p for p in sorted(cases_dir.iterdir()) if p.is_dir() and (p / "truth.json").exists()]
    if not case_dirs:
        msg = "No valid case directories with truth.json found in data/cases/."
        print(msg)
        eval_md_path.write_text(f"# Damga AI Pipeline Evaluation\n\n{msg}\n", encoding="utf-8")
        return {"status": "skipped", "message": msg}

    case_results: List[Dict[str, Any]] = []
    all_rules = set()
    rule_stats: Dict[str, Dict[str, int]] = {}
    status_matrix: Dict[str, Dict[str, int]] = {
        "green": {"green": 0, "yellow": 0, "red": 0, "missing": 0},
        "yellow": {"green": 0, "yellow": 0, "red": 0, "missing": 0},
        "red": {"green": 0, "yellow": 0, "red": 0, "missing": 0},
        "missing": {"green": 0, "yellow": 0, "red": 0, "missing": 0},
    }

    correct_status_count = 0

    for cdir in case_dirs:
        case_id = cdir.name
        truth_path = cdir / "truth.json"
        truth = json.loads(truth_path.read_text(encoding="utf-8"))

        expected_status = truth.get("expected_status", "green").lower()
        expected_flags = set(truth.get("expected_flags", []))

        for r in expected_flags:
            all_rules.add(r)

        try:
            res = run_pipeline(cdir, attempt_index=0, live=live)
            actual_status = res.get("status", "green").lower()
            actual_flags = set(f.get("rule", "") for f in res.get("flags", []))
            for r in actual_flags:
                all_rules.add(r)

            is_status_correct = (actual_status == expected_status)
            if is_status_correct:
                correct_status_count += 1

            if expected_status in status_matrix and actual_status in status_matrix[expected_status]:
                status_matrix[expected_status][actual_status] += 1

            case_results.append({
                "case_id": case_id,
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_flags": sorted(list(expected_flags)),
                "actual_flags": sorted(list(actual_flags)),
                "status_match": is_status_correct,
                "flag_match": expected_flags == actual_flags,
                "result_hash": res.get("result_hash"),
            })

            # Rule-level stats
            for r in expected_flags.union(actual_flags):
                if r not in rule_stats:
                    rule_stats[r] = {"tp": 0, "fp": 0, "fn": 0}
                if r in expected_flags and r in actual_flags:
                    rule_stats[r]["tp"] += 1
                elif r not in expected_flags and r in actual_flags:
                    rule_stats[r]["fp"] += 1
                elif r in expected_flags and r not in actual_flags:
                    rule_stats[r]["fn"] += 1

        except Exception as e:
            case_results.append({
                "case_id": case_id,
                "error": str(e),
                "status_match": False,
                "flag_match": False,
            })

    total_cases = len(case_dirs)
    status_accuracy = correct_status_count / total_cases if total_cases > 0 else 0.0

    # Build markdown report
    lines = [
        "# Damga AI Pipeline Evaluation Report",
        "",
        f"- **Total Cases Evaluated**: {total_cases}",
        f"- **Status Accuracy**: {status_accuracy:.1%} ({correct_status_count}/{total_cases})",
        "",
        "## Confusion Matrix (Rows = Expected, Columns = Actual)",
        "",
        "| Expected \\ Actual | Green | Yellow | Red | Missing |",
        "|---|---|---|---|---|",
    ]

    for exp in ["green", "yellow", "red", "missing"]:
        row = status_matrix[exp]
        lines.append(f"| **{exp.upper()}** | {row['green']} | {row['yellow']} | {row['red']} | {row['missing']} |")

    lines.extend([
        "",
        "## Rule Detection Performance",
        "",
        "| Rule ID | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|",
    ])

    for r in sorted(rule_stats.keys()):
        s = rule_stats[r]
        tp, fp, fn = s["tp"], s["fp"], s["fn"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        lines.append(f"| `{r}` | {tp} | {fp} | {fn} | {prec:.1%} | {rec:.1%} | {f1:.1%} |")

    lines.extend([
        "",
        "## Case Details",
        "",
        "| Case ID | Expected Status | Actual Status | Expected Flags | Actual Flags | Status Match |",
        "|---|---|---|---|---|---|",
    ])

    for c in case_results:
        exp_f = ", ".join(c.get("expected_flags", [])) or "-"
        act_f = ", ".join(c.get("actual_flags", [])) or "-"
        sm = "PASS" if c.get("status_match") else "FAIL"
        lines.append(f"| `{c['case_id']}` | `{c.get('expected_status')}` | `{c.get('actual_status')}` | {exp_f} | {act_f} | {sm} |")

    report_text = "\n".join(lines) + "\n"
    eval_md_path.write_text(report_text, encoding="utf-8")
    print(report_text)

    return {
        "status": "success",
        "total_cases": total_cases,
        "accuracy": status_accuracy,
        "case_results": case_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Damga AI Pipeline Evaluation")
    parser.add_argument("--live", action="store_true", help="Run live Mistral extraction")
    args = parser.parse_args()
    run_evaluation(live=args.live)


if __name__ == "__main__":
    main()
