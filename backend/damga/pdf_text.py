import io
import re
import unicodedata
from pathlib import Path
from typing import List, Union
import pypdf


def normalize_whitespace(text: str) -> str:
    """Normalizes unicode and collapses multiple whitespace characters into single space."""
    if not text:
        return ""
    # NFKC normalizes compatibility characters, full-width, non-breaking spaces
    text = unicodedata.normalize("NFKC", text)
    # Replace non-breaking spaces and other special spaces
    text = text.replace("\u00a0", " ").replace("\u202f", " ")
    # Replace any sequence of whitespace with single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_pdf(source: Union[bytes, str, Path]) -> str:
    """Extracts text from all pages of a PDF using pypdf."""
    if isinstance(source, (str, Path)):
        reader = pypdf.PdfReader(str(source))
    else:
        reader = pypdf.PdfReader(io.BytesIO(source))

    pages_text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            pages_text.append(page_text)

    return "\n\n".join(pages_text)


def split_into_paragraphs(text: str) -> List[str]:
    """Splits text into paragraphs by blank lines or distinct blocks."""
    raw_paras = re.split(r"\n\s*\n", text)
    cleaned = [p.strip() for p in raw_paras if p.strip()]
    return cleaned
