"""Short held-out test: regex screen vs guard models on rows the regex was never tuned on.

Attacks: public rows that are NOT in data/injection/attacks.jsonl (deepset, Lakera gandalf, BIPIA test split).
Benign: unseen deepset benign rows plus real paragraphs from our own evidence PDFs (the text the screen really sees).

Usage:
    backend/.venv/bin/python -m damga.eval_guard --models openai/gpt-oss-safeguard-20b [other/model ...]
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import random
import time

from damga.guard import check_paragraph_guard
from damga.injection import check_paragraph_injection
from damga.pdf_text import extract_text_from_pdf, split_into_paragraphs

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "injection" / "raw"
PER_GROUP = 15


def build_holdout(seed: int = 7):
    used = {json.loads(line)["text"] for line in (ROOT / "data" / "injection" / "attacks.jsonl").read_text().splitlines() if line.strip()}
    rng = random.Random(seed)

    def pick(rows, n):
        rows = sorted({r for r in rows if r not in used and len(r) > 15})
        return rng.sample(rows, min(n, len(rows)))

    deepset = json.loads((RAW / "deepset_train.json").read_text())
    lakera = json.loads((RAW / "lakera_train.json").read_text())
    bipia = json.loads((RAW / "bipia_text_attack_test.json").read_text())
    attacks = (
        [("deepset", t) for t in pick([r["text"] for r in deepset if r["label"] == 1], PER_GROUP)]
        + [("lakera", t) for t in pick([r["text"] for r in lakera], PER_GROUP)]
        + [("bipia-test", t) for t in pick([t for rows in bipia.values() for t in rows], PER_GROUP)]
    )
    pdf_paras = []
    for case in ("honest-01", "cheat-pigiron-invoice-01", "yellow-low-electricity-01"):
        for pdf in sorted((ROOT / "data" / "cases" / case / "docs").glob("*.pdf")):
            pdf_paras += [p for p in split_into_paragraphs(extract_text_from_pdf(pdf.read_bytes())) if len(p) > 40]
    benign = (
        [("deepset-benign", t) for t in pick([r["text"] for r in deepset if r["label"] == 0], PER_GROUP)]
        + [("evidence-pdf", t) for t in pick(pdf_paras, 2 * PER_GROUP)]
    )
    return attacks, benign


def predict(fn, rows):
    """One prediction per row: True/False, or None when the call failed (never counted as clean)."""
    def run(text):
        for wait in (2, 5, 10, 20, None):
            try:
                return fn(text)[0], None
            except Exception as e:
                # Rate limits are not a verdict: back off and ask again.
                if wait is None or "429" not in str(e):
                    return None, str(e)[:120]
                time.sleep(wait)

    with ThreadPoolExecutor(max_workers=3) as pool:
        return list(pool.map(run, [t for _, t, _ in rows]))


def score(name, preds, rows, seconds):
    n_att = sum(1 for _, _, y in rows if y == 1)
    n_ben = len(rows) - n_att
    errors = [e for _, e in preds if e]
    return {
        "screen": name,
        "recall": round(sum(1 for (_, _, y), (p, _) in zip(rows, preds) if y == 1 and p) / n_att, 3),
        "false_positive_rate": round(sum(1 for (_, _, y), (p, _) in zip(rows, preds) if y == 0 and p) / n_ben, 3),
        "errors": len(errors),
        "seconds": seconds,
        "missed_attacks": [(s, t[:90]) for (s, t, y), (p, _) in zip(rows, preds) if y == 1 and p is False],
        "false_alarms": [(s, t[:90]) for (s, t, y), (p, _) in zip(rows, preds) if y == 0 and p],
        "first_error": errors[0] if errors else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=[])
    ap.add_argument("--out", default=str(ROOT / "research" / "guard-test" / "results.json"))
    args = ap.parse_args()

    attacks, benign = build_holdout()
    print(f"Held-out set: {len(attacks)} attacks, {len(benign)} benign ({sum(1 for s, _ in benign if s == 'evidence-pdf')} from our PDFs)\n")
    rows = [(src, text, 1) for src, text in attacks] + [(src, text, 0) for src, text in benign]
    regex = [(check_paragraph_injection(t)[0], None) for _, t, _ in rows]
    results = [score("regex (current)", regex, rows, 0.0)]
    for m in args.models:
        start = time.time()
        preds = predict(lambda t, m=m: check_paragraph_guard(t, model=m), rows)
        seconds = round(time.time() - start, 1)
        results.append(score(m, preds, rows, seconds))
        # The pipeline runs both screens: a paragraph is dropped when either one flags it.
        both = [(True, None) if r else g for (r, _), g in zip(regex, preds)]
        results.append(score(f"regex + {m}", both, rows, seconds))

    print(f"{'screen':<48} {'recall':>7} {'FP rate':>8} {'errors':>7} {'sec':>6}")
    for r in results:
        print(f"{r['screen']:<48} {r['recall']:>7.1%} {r['false_positive_rate']:>8.1%} {r['errors']:>7} {r['seconds']:>6}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"attacks": attacks, "benign": benign, "results": results}, indent=2, ensure_ascii=False))
    print(f"\nDetails: {out}")


if __name__ == "__main__":
    main()
