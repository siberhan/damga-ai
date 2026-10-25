#!/usr/bin/env python3
"""
Reproducible build script for prompt injection test dataset.
Damga AI - Solo entry for IEEE ClimateChain Global Hackathon 2026.

Collects and filters 90 public prompt-injection test texts (data only):
- 20 attacks from Microsoft BIPIA
- 20 attacks from deepset/prompt-injections
- 20 attacks from Lakera/gandalf_ignore_instructions
- 30 benign texts from deepset/prompt-injections

NO attack or benign text was written, paraphrased, or invented by us.
All texts are exact verbatim copies from public benchmark datasets.

Usage:
    python3 data/injection/build.py
"""

import os
import sys
import json
import urllib.request
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUTPUT_JSONL = os.path.join(SCRIPT_DIR, "attacks.jsonl")

# Exact source metadata
SOURCES = {
    "bipia": {
        "name": "microsoft/BIPIA",
        "url": "https://github.com/microsoft/BIPIA",
        "license": "MIT",
    },
    "deepset": {
        "name": "deepset/prompt-injections",
        "url": "https://huggingface.co/datasets/deepset/prompt-injections",
        "license": "Apache-2.0",
    },
    "lakera": {
        "name": "Lakera/gandalf_ignore_instructions",
        "url": "https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions",
        "license": "MIT",
    },
}

# German markers to filter out non-English samples from deepset
GERMAN_MARKERS = {
    "ich", "nicht", "der", "die", "das", "und", "ist", "für",
    "anweisungen", "bitte", "aufgabe", "schreibe", "wieso", "stopp"
}

def is_german(text: str) -> bool:
    """Check if text contains obvious German stopwords."""
    cleaned = text.lower().replace(".", " ").replace(",", " ").replace("!", " ").replace("?", " ")
    words = set(cleaned.split())
    return any(marker in words for marker in GERMAN_MARKERS)


def download_raw_files():
    """Download raw datasets from public repositories if not already present."""
    os.makedirs(RAW_DIR, exist_ok=True)
    
    # 1. BIPIA text attack files
    bipia_files = [
        ("text_attack_train.json", "bipia_text_attack_train.json"),
        ("text_attack_test.json", "bipia_text_attack_test.json"),
    ]
    for src_name, dst_name in bipia_files:
        dst_path = os.path.join(RAW_DIR, dst_name)
        if not os.path.exists(dst_path):
            url = f"https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/{src_name}"
            print(f"Downloading {url} -> {dst_path}...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                with open(dst_path, "wb") as f:
                    f.write(resp.read())

    # 2. deepset/prompt-injections
    deepset_path = os.path.join(RAW_DIR, "deepset_train.json")
    if not os.path.exists(deepset_path):
        print(f"Downloading deepset/prompt-injections -> {deepset_path}...")
        deepset_rows = []
        offset = 0
        while True:
            url = f"https://datasets-server.huggingface.co/rows?dataset=deepset/prompt-injections&config=default&split=train&offset={offset}&length=100"
            for attempt in range(5):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        break
                except Exception as e:
                    if attempt == 4:
                        raise
                    time.sleep(2 ** attempt)
            rows = data.get("rows", [])
            if not rows:
                break
            for r in rows:
                deepset_rows.append(r["row"])
            offset += len(rows)
            if offset >= data.get("num_rows_total", 0):
                break
            time.sleep(0.3)
        with open(deepset_path, "w", encoding="utf-8") as f:
            json.dump(deepset_rows, f, indent=2, ensure_ascii=False)

    # 3. Lakera/gandalf_ignore_instructions
    lakera_path = os.path.join(RAW_DIR, "lakera_train.json")
    if not os.path.exists(lakera_path):
        print(f"Downloading Lakera/gandalf_ignore_instructions -> {lakera_path}...")
        lakera_rows = []
        offset = 0
        while True:
            url = f"https://datasets-server.huggingface.co/rows?dataset=Lakera/gandalf_ignore_instructions&config=default&split=train&offset={offset}&length=100"
            for attempt in range(5):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        break
                except Exception as e:
                    if attempt == 4:
                        raise
                    time.sleep(2 ** attempt)
            rows = data.get("rows", [])
            if not rows:
                break
            for r in rows:
                lakera_rows.append(r["row"])
            offset += len(rows)
            if offset >= data.get("num_rows_total", 0):
                break
            time.sleep(0.3)
        with open(lakera_path, "w", encoding="utf-8") as f:
            json.dump(lakera_rows, f, indent=2, ensure_ascii=False)


def build():
    download_raw_files()

    bipia_train_path = os.path.join(RAW_DIR, "bipia_text_attack_train.json")
    bipia_test_path = os.path.join(RAW_DIR, "bipia_text_attack_test.json")
    deepset_path = os.path.join(RAW_DIR, "deepset_train.json")
    lakera_path = os.path.join(RAW_DIR, "lakera_train.json")

    # 1. BIPIA Selection: 20 attacks across 4 core adversarial categories
    with open(bipia_train_path, "r", encoding="utf-8") as f:
        bipia_train = json.load(f)
    with open(bipia_test_path, "r", encoding="utf-8") as f:
        bipia_test = json.load(f)

    bipia_items = []
    
    # 5 from Instruction (train)
    for idx, text in enumerate(bipia_train["Instruction"]):
        bipia_items.append({
            "id": f"bipia-{len(bipia_items)+1:03d}",
            "source": SOURCES["bipia"]["name"],
            "source_ref": f"benchmark/text_attack_train.json#Instruction[{idx}]",
            "license": SOURCES["bipia"]["license"],
            "label": "attack",
            "text": text,
        })

    # 5 from Substitution Ciphers (test)
    for idx, text in enumerate(bipia_test["Substitution Ciphers"]):
        bipia_items.append({
            "id": f"bipia-{len(bipia_items)+1:03d}",
            "source": SOURCES["bipia"]["name"],
            "source_ref": f"benchmark/text_attack_test.json#Substitution Ciphers[{idx}]",
            "license": SOURCES["bipia"]["license"],
            "label": "attack",
            "text": text,
        })

    # 5 from Base Encoding (test)
    for idx, text in enumerate(bipia_test["Base Encoding"]):
        bipia_items.append({
            "id": f"bipia-{len(bipia_items)+1:03d}",
            "source": SOURCES["bipia"]["name"],
            "source_ref": f"benchmark/text_attack_test.json#Base Encoding[{idx}]",
            "license": SOURCES["bipia"]["license"],
            "label": "attack",
            "text": text,
        })

    # 5 from Misinformation & Propaganda (test)
    for idx, text in enumerate(bipia_test["Misinformation & Propaganda"]):
        bipia_items.append({
            "id": f"bipia-{len(bipia_items)+1:03d}",
            "source": SOURCES["bipia"]["name"],
            "source_ref": f"benchmark/text_attack_test.json#Misinformation & Propaganda[{idx}]",
            "license": SOURCES["bipia"]["license"],
            "label": "attack",
            "text": text,
        })

    assert len(bipia_items) == 20, f"Expected 20 BIPIA items, got {len(bipia_items)}"

    # 2. deepset Selection: 20 attacks + 30 benign
    with open(deepset_path, "r", encoding="utf-8") as f:
        deepset_rows = json.load(f)

    deepset_attack_keywords = [
        "ignore", "forget", "instead", "new task", "instruction",
        "output", "disregard", "override", "stop", "reveal", "bypass"
    ]

    deepset_attacks = []
    for idx, row in enumerate(deepset_rows):
        if row.get("label") == 1:
            text = row.get("text", "").strip()
            if len(text) <= 600 and not is_german(text):
                lower_text = text.lower()
                if any(kw in lower_text for kw in deepset_attack_keywords):
                    deepset_attacks.append({
                        "id": f"deepset-{len(deepset_attacks)+1:03d}",
                        "source": SOURCES["deepset"]["name"],
                        "source_ref": f"train/row_{idx}",
                        "license": SOURCES["deepset"]["license"],
                        "label": "attack",
                        "text": text,
                    })
                    if len(deepset_attacks) == 20:
                        break

    assert len(deepset_attacks) == 20, f"Expected 20 deepset attacks, got {len(deepset_attacks)}"

    deepset_benign = []
    for idx, row in enumerate(deepset_rows):
        if row.get("label") == 0:
            text = row.get("text", "").strip()
            if len(text) <= 600 and not is_german(text):
                deepset_benign.append({
                    "id": f"deepset-benign-{len(deepset_benign)+1:03d}",
                    "source": SOURCES["deepset"]["name"],
                    "source_ref": f"train/row_{idx}",
                    "license": SOURCES["deepset"]["license"],
                    "label": "benign",
                    "text": text,
                })
                if len(deepset_benign) == 30:
                    break

    assert len(deepset_benign) == 30, f"Expected 30 deepset benign items, got {len(deepset_benign)}"

    # 3. Lakera Selection: 20 attacks
    with open(lakera_path, "r", encoding="utf-8") as f:
        lakera_rows = json.load(f)

    lakera_items = []
    for idx, row in enumerate(lakera_rows):
        text = row.get("text", "").strip()
        if len(text) <= 600:
            lakera_items.append({
                "id": f"lakera-{len(lakera_items)+1:03d}",
                "source": SOURCES["lakera"]["name"],
                "source_ref": f"train/row_{idx}",
                "license": SOURCES["lakera"]["license"],
                "label": "attack",
                "text": text,
            })
            if len(lakera_items) == 20:
                break

    assert len(lakera_items) == 20, f"Expected 20 Lakera items, got {len(lakera_items)}"

    # Combine all 90 items in structured order
    all_records = bipia_items + deepset_attacks + lakera_items + deepset_benign

    # Integrity verification
    assert len(all_records) == 90, f"Expected 90 records, got {len(all_records)}"
    all_ids = [r["id"] for r in all_records]
    assert len(set(all_ids)) == 90, f"Duplicate IDs found in {len(all_ids)} records"

    # Write attacks.jsonl
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Successfully generated {OUTPUT_JSONL}:")
    print(f"  - microsoft/BIPIA: 20 attacks")
    print(f"  - deepset/prompt-injections: 20 attacks, 30 benign")
    print(f"  - Lakera/gandalf_ignore_instructions: 20 attacks")
    print(f"  - Total: {len(all_records)} lines (60 attacks, 30 benign)")
    print(f"  - Unique IDs: {len(set(all_ids))}")


if __name__ == "__main__":
    build()
