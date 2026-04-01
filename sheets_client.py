"""Google Sheets client for reading and writing lead data."""

from __future__ import annotations

import logging
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

import config
from models import Lead, LeadStatus

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_EXPECTED_HEADERS = [
    "first_name",
    "last_name",
    "email",
    "company",
    "title",
    "phone",
    "linkedin_url",
    "status",
    "notes",
]


class SheetsClientError(Exception):
    """Raised for Google Sheets operation failures."""


class SheetsClient:
    """Thin wrapper around gspread for lead-specific sheet operations."""

    def __init__(self) -> None:
        try:
            creds = Credentials.from_service_account_file(
                config.GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=_SCOPES
            )
            gc = gspread.authorize(creds)
            spreadsheet = gc.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)
            self._sheet = spreadsheet.worksheet(config.GOOGLE_SHEETS_SHEET_NAME)
        except FileNotFoundError as exc:
            raise SheetsClientError(
                f"Credentials file not found: {config.GOOGLE_SHEETS_CREDENTIALS_FILE}"
            ) from exc
        except gspread.exceptions.SpreadsheetNotFound as exc:
            raise SheetsClientError(
                f"Spreadsheet not found: {config.GOOGLE_SHEETS_SPREADSHEET_ID}"
            ) from exc
        except Exception as exc:
            raise SheetsClientError(
                f"Failed to initialise Sheets client: {exc}"
            ) from exc

    def _validate_headers(self, headers: list[str]) -> None:
        if headers != _EXPECTED_HEADERS:
            raise SheetsClientError(
                f"Unexpected sheet headers: got {headers}, "
                f"expected {_EXPECTED_HEADERS}"
            )

    def get_all_leads(self) -> list[tuple[int, Lead]]:
        """Read every row and return (row_index, Lead) pairs.

        row_index is 1-based (row 1 is the header), so data starts at row 2.
        """
        try:
            records: list[dict[str, Any]] = self._sheet.get_all_records()
        except Exception as exc:
            raise SheetsClientError(f"Failed to read leads: {exc}") from exc

        if records:
            self._validate_headers(list(records[0].keys()))

        leads: list[tuple[int, Lead]] = []
        for idx, row in enumerate(records, start=2):
            try:
                leads.append((idx, Lead(**row)))
            except Exception:
                logger.warning("Skipping invalid row %d: validation failed", idx)
        return leads

    def get_leads_by_status(self, status: LeadStatus) -> list[tuple[int, Lead]]:
        return [
            (row_idx, lead)
            for row_idx, lead in self.get_all_leads()
            if lead.status == status
        ]

    def update_lead_row(self, row_index: int, lead: Lead) -> None:
        """Update a single row (1-indexed, header is row 1)."""
        if row_index < 2:
            raise ValueError("Row index must be >= 2 (row 1 is the header)")
        try:
            values = [
                lead.first_name,
                lead.last_name,
                lead.email,
                lead.company,
                lead.title,
                lead.phone,
                lead.linkedin_url,
                lead.status.value,
                lead.notes,
            ]
            self._sheet.update(
                f"A{row_index}:{chr(64 + len(values))}{row_index}",
                [values],
            )
            logger.info("Updated row %d for %s", row_index, lead.email)
        except Exception as exc:
            raise SheetsClientError(
                f"Failed to update row {row_index}: {exc}"
            ) from exc

    def append_lead(self, lead: Lead) -> None:
        try:
            self._sheet.append_row(
                [
                    lead.first_name,
                    lead.last_name,
                    lead.email,
                    lead.company,
                    lead.title,
                    lead.phone,
                    lead.linkedin_url,
                    lead.status.value,
                    lead.notes,
                ]
            )
            logger.info("Appended lead: %s", lead.email)
        except Exception as exc:
            raise SheetsClientError(f"Failed to append lead: {exc}") from exc
