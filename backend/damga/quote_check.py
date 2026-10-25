import re
from typing import Set, Tuple
from damga.pdf_text import normalize_whitespace


def extract_number_candidates(token: str) -> Set[float]:
    """Parses various number formats tolerant to US/EU thousands and decimal separators."""
    token = token.strip().rstrip(".,;:")
    candidates: Set[float] = set()

    # 1. Direct parse (e.g. "800.0", "1234.5")
    try:
        candidates.add(float(token))
    except ValueError:
        pass

    # 2. US format: 1,234.5 or 1,234 -> strip comma
    try:
        candidates.add(float(token.replace(",", "")))
    except ValueError:
        pass

    # 3. EU format: 1.234,5 -> strip dot, comma to dot
    try:
        candidates.add(float(token.replace(".", "").replace(",", ".")))
    except ValueError:
        pass

    # 4. Comma decimal: 800,00 -> 800.00
    try:
        candidates.add(float(token.replace(",", ".")))
    except ValueError:
        pass

    # 5. Space thousands separator: 1 234.5 -> 1234.5
    try:
        candidates.add(float(token.replace(" ", "")))
    except ValueError:
        pass

    # 6. Space thousands and comma decimal: 1 234,5 -> 1234.5
    try:
        candidates.add(float(token.replace(" ", "").replace(",", ".")))
    except ValueError:
        pass

    return candidates


def quote_contains_value(quote: str, expected_val: float, tolerance: float = 1e-4) -> bool:
    """Checks whether the quote contains a number matching expected_val."""
    tokens = re.findall(r"[0-9]+(?:[., ][0-9]+)*", quote)
    for tok in tokens:
        candidates = extract_number_candidates(tok)
        # "Q1 68,000.0" joins into one token through the space; try each part on its own too.
        for part in tok.split(" "):
            candidates |= extract_number_candidates(part)
        for cand in candidates:
            # Check relative and absolute difference
            if abs(cand - expected_val) <= tolerance or (
                expected_val != 0 and abs(cand - expected_val) / abs(expected_val) <= tolerance
            ):
                return True
    return False


def verify_quote(quote: str, value: float, doc_text: str) -> Tuple[bool, str]:
    """
    Verifies:
    1. Quote is verbatim in doc_text (after whitespace normalization).
    2. The number in the quote matches the extracted value.
    Returns (passed: bool, status: "pass" | "fail").
    """
    if not quote or not doc_text:
        return False, "fail"

    norm_quote = normalize_whitespace(quote).lower()
    norm_doc = normalize_whitespace(doc_text).lower()

    # Check verbatim occurrence
    if norm_quote not in norm_doc:
        return False, "fail"

    # Check number match
    if not quote_contains_value(quote, value):
        return False, "fail"

    return True, "pass"
