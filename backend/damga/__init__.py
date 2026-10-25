"""Damga AI backend package."""
from pathlib import Path

from dotenv import load_dotenv

__version__ = "0.1.0"

# Keys and the registry address live only in the root .env (never in code or the repo).
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
