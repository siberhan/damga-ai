import re
from typing import Any, Dict, List, Tuple
from damga.pdf_text import split_into_paragraphs

# Heuristics for prompt-injection screening (spec section 10 step 2)
INJECTION_RULES: List[Tuple[str, str]] = [
    (r"(?i)\b(ignore|disregard|forget|override)\s+(all|any|the|previous|above|preceding|prior)\b", "override_instruction"),
    (r"(?i)\bforget\s+(everything|about\s+all)\b", "override_instruction"),
    (r"(?i)\b(don\'?t|do\s+not)\s+follow\s+any\s+(previous|prior)\b", "override_instruction"),
    (r"(?i)\b(leave|remove|drop)\s+all\s+(the\s+)?previous\b", "override_instruction"),
    (r"(?i)\b(new\s+tasks?\s+follow|new\s+instructions?\s+follow|perform\s+a\s+different\s+task)\b", "override_instruction"),
    (r"(?i)\b(now\s+focus\s+on\s+your\s+new\s+task|concentrate\s+on\s+your\s+new\s+task|start\s+with\s+a\s+new\s+task)\b", "override_instruction"),
    (r"(?i)\b(in|to|for|with)\s+your\s+(answer|response|reply|output)\b", "instruction_to_model"),
    (r"(?i)\b(modify|alter|augment|integrate|encrypt|encode|render|provide|enhance)\s+(your\s+)?(answer|response|reply|message)\b", "instruction_to_model"),
    (r"(?i)\b(reply|respond)\s+(using|with)\b", "instruction_to_model"),
    (r"(?i)\b(list\s+your|repeat\s+the\s+last|tell\s+me\s+your)\s+.*instructions?\b", "instruction_to_model"),
    (r"(?i)\byou\s+now\s+(take|follow|have)\s+instructions\b", "instruction_to_model"),
    (r"(?i)\b(act\s+as\s+a|you\s+are\s+now|pretend\s+to\s+be)\b", "role_play"),
    (r"(?i)\b(do\s+not\s+answer|instead\s+(output|print|write|say))\b", "override_instruction"),
    (r"(?i)\b(caesar\s+cipher|substitution\s+cipher|monoalphabetic\s+cipher)\b", "encoding_attack"),
    (r"(?i)\b(base64|base32|base16|base58)\b.*\b(response|answer|reply|format|encoding)\b", "encoding_attack"),
    (r"(?i)\b(system\s*prompt|system\s*instructions?|developer\s*mode|jailbreak|exploiting\s*ai)\b", "role_play"),
    (r"(?i)<system>|\[INST\]|<<SYS>>|<\|im_start\|>", "role_tags"),
    (r"(?i)\b(set\s+.*to\s+0|approve\s+this|mark\s+as\s+green|ignore\s+pig\s+iron|bypass\s+check)\b", "domain_override"),
    (r"(?i)\battention\s*-\s*stop\s*-\s*i\s+urgently\s+need\s+your\s+help\b", "override_instruction"),
]


def check_paragraph_injection(paragraph: str) -> Tuple[bool, str]:
    """
    Checks if a single paragraph contains prompt injection patterns.
    Returns (is_injected, reason).
    """
    cleaned = paragraph.strip()
    if not cleaned:
        return False, ""

    for pattern, reason in INJECTION_RULES:
        if re.search(pattern, cleaned):
            return True, reason

    return False, ""


def screen_text(text: str, use_guard: bool = False) -> Dict[str, Any]:
    """
    Screens document text line by line (the PDFs have no blank lines between paragraphs, so a
    paragraph split would drop a whole document for one bad line).
    1. Regex rules on every line.
    2. With use_guard: the guard model reads the whole document once; only if it says an
       injection may be there, it reads each remaining line and drops the flagged ones.
    Returns {"kept_text": str, "removed": [{"text", "reason", "source_set"}], "guard": {...} or None}.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    kept: List[str] = []
    removed: List[Dict[str, Any]] = []

    for line in lines:
        is_attack, reason = check_paragraph_injection(line)
        if is_attack:
            removed.append({"text": line, "reason": reason, "source_set": None})
        else:
            kept.append(line)

    guard_info = None
    if use_guard and kept:
        from concurrent.futures import ThreadPoolExecutor
        from damga.guard import GUARD_THRESHOLD, check_document_guard, check_paragraph_guard, get_guard_model

        model = get_guard_model()
        doc_p = check_document_guard("\n".join(kept), model=model)
        guard_info = {"model": model, "doc_p": round(doc_p, 4), "lines_checked": 0}
        if doc_p >= GUARD_THRESHOLD:
            with ThreadPoolExecutor(max_workers=4) as pool:
                verdicts = list(pool.map(lambda ln: check_paragraph_guard(ln, model=model), kept))
            guard_info["lines_checked"] = len(kept)
            still_kept = []
            for line, (is_attack, reason) in zip(kept, verdicts):
                if is_attack:
                    removed.append({"text": line, "reason": reason, "source_set": None})
                else:
                    still_kept.append(line)
            kept = still_kept

    return {
        "kept_text": "\n".join(kept),
        "removed": removed,
        "guard": guard_info,
    }
