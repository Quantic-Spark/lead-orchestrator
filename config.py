"""Centralized configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class _MissingVars(Exception):
    """Raised when required environment variables are absent."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise _MissingVars(f"Required environment variable '{name}' is not set")
    return value


def _optional_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _resolve_credentials_path(env_var: str) -> Path:
    raw = _require_env(env_var)
    path = Path(raw).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Credentials file referenced by {env_var} not found: {path}"
        )
    return path


# --- Google Sheets ---
GOOGLE_SHEETS_CREDENTIALS_FILE = _optional_env(
    "GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json"
)
GOOGLE_SHEETS_SPREADSHEET_ID = _optional_env("GOOGLE_SHEETS_SPREADSHEET_ID")
GOOGLE_SHEETS_SHEET_NAME = _optional_env("GOOGLE_SHEETS_SHEET_NAME", "Leads")

# --- Gmail ---
GMAIL_CREDENTIALS_FILE = _optional_env(
    "GMAIL_CREDENTIALS_FILE", "gmail_credentials.json"
)
GMAIL_SENDER_EMAIL = _optional_env("GMAIL_SENDER_EMAIL")

# --- ZoomInfo ---
ZOOMINFO_API_URL = _optional_env("ZOOMINFO_API_URL", "https://api.zoominfo.com")
ZOOMINFO_USERNAME = _optional_env("ZOOMINFO_USERNAME")
ZOOMINFO_PASSWORD = _optional_env("ZOOMINFO_PASSWORD")

# --- App-wide ---
LOG_LEVEL = _optional_env("LOG_LEVEL", "INFO").upper()
DRY_RUN = _optional_env("DRY_RUN", "false").lower() in ("true", "1", "yes")


def configure_logging() -> None:
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def validate_required_settings(services: list[str] | None = None) -> None:
    """Validate that required config values are present for the requested services.

    Raises _MissingVars with a combined message for all missing variables.
    """
    missing: list[str] = []
    services = services or ["sheets", "gmail", "zoominfo"]

    checks: dict[str, list[tuple[str, str]]] = {
        "sheets": [
            (GOOGLE_SHEETS_SPREADSHEET_ID, "GOOGLE_SHEETS_SPREADSHEET_ID"),
        ],
        "gmail": [
            (GMAIL_SENDER_EMAIL, "GMAIL_SENDER_EMAIL"),
        ],
        "zoominfo": [
            (ZOOMINFO_USERNAME, "ZOOMINFO_USERNAME"),
            (ZOOMINFO_PASSWORD, "ZOOMINFO_PASSWORD"),
        ],
    }

    for svc in services:
        for value, var_name in checks.get(svc, []):
            if not value:
                missing.append(var_name)

    if missing:
        raise _MissingVars(
            "Missing required environment variables: " + ", ".join(missing)
        )
