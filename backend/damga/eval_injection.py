import json
from pathlib import Path
from damga.injection import check_paragraph_injection


def run_injection_eval(attacks_path: Path | None = None) -> dict:
    """Evaluates injection screen against attacks.jsonl dataset."""
    if attacks_path is None:
        backend_dir = Path(__file__).resolve().parent.parent
        attacks_path = backend_dir.parent / "data" / "injection" / "attacks.jsonl"

    if not attacks_path.exists():
        print(f"Injection attacks dataset not found at: {attacks_path}")
        return {"status": "skipped", "reason": "dataset not found"}

    attacks = []
    benign = []

    with open(attacks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("label") == "attack":
                attacks.append(entry)
            elif entry.get("label") == "benign":
                benign.append(entry)

    detected_attacks = 0
    false_positives = 0

    for a in attacks:
        is_attack, _ = check_paragraph_injection(a.get("text", ""))
        if is_attack:
            detected_attacks += 1

    for b in benign:
        is_attack, _ = check_paragraph_injection(b.get("text", ""))
        if is_attack:
            false_positives += 1

    total_attacks = len(attacks)
    total_benign = len(benign)

    recall = (detected_attacks / total_attacks) if total_attacks > 0 else 0.0
    fp_rate = (false_positives / total_benign) if total_benign > 0 else 0.0

    print("========================================")
    print("Prompt Injection Screen Evaluation")
    print("========================================")
    print(f"Total attacks: {total_attacks}")
    print(f"Attacks detected: {detected_attacks} ({recall:.1%})")
    print(f"Total benign: {total_benign}")
    print(f"False positives: {false_positives} ({fp_rate:.1%})")
    print("========================================")

    return {
        "status": "success",
        "total_attacks": total_attacks,
        "detected_attacks": detected_attacks,
        "recall": recall,
        "total_benign": total_benign,
        "false_positives": false_positives,
        "fp_rate": fp_rate,
    }


if __name__ == "__main__":
    run_injection_eval()
