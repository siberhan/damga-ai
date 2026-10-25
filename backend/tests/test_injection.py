import json
from pathlib import Path
import pytest
from damga.eval_injection import run_injection_eval
from damga.pipeline import get_project_root


def test_injection_screen_benchmark():
    attacks_path = get_project_root() / "data" / "injection" / "attacks.jsonl"
    if not attacks_path.exists():
        pytest.skip("data/injection/attacks.jsonl does not exist; skipping injection screen benchmark test.")

    res = run_injection_eval(attacks_path)
    assert res["status"] == "success"
    # Recall must be high on attack samples
    assert res["recall"] >= 0.90, f"Expected recall >= 90%, got {res['recall']:.1%}"
    # False-positive rate on benign texts must be very low
    assert res["fp_rate"] <= 0.05, f"Expected FP rate <= 5%, got {res['fp_rate']:.1%}"
