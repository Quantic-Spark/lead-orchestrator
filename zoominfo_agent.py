"""ZoomInfo agent for enriching lead data via the ZoomInfo API."""

from __future__ import annotations

import logging

import requests

import config
from models import EnrichmentData, Lead

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 30


class ZoomInfoAgentError(Exception):
    """Raised for ZoomInfo API operation failures."""


class ZoomInfoAgent:
    """Authenticates with ZoomInfo and retrieves enrichment data for leads."""

    def __init__(self) -> None:
        self._base_url = config.ZOOMINFO_API_URL.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._authenticate()

    def _authenticate(self) -> None:
        try:
            resp = self._session.post(
                f"{self._base_url}/authenticate",
                json={
                    "username": config.ZOOMINFO_USERNAME,
                    "password": config.ZOOMINFO_PASSWORD,
                },
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            token: str = resp.json().get("jwt", "")
            if not token:
                raise ZoomInfoAgentError("Authentication returned empty token")
            self._session.headers["Authorization"] = f"Bearer {token}"
            logger.info("Authenticated with ZoomInfo API")
        except requests.RequestException as exc:
            raise ZoomInfoAgentError(f"ZoomInfo authentication failed: {exc}")

    def enrich_lead(self, lead: Lead) -> EnrichmentData:
        """Look up a lead by email and return enrichment data."""
        try:
            resp = self._session.post(
                f"{self._base_url}/search/contact",
                json={
                    "emailAddress": lead.email,
                    "outputFields": [
                        "company.revenue",
                        "company.employeeCount",
                        "company.industry",
                        "company.website",
                        "directPhoneNumber",
                    ],
                },
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise ZoomInfoAgentError(
                f"ZoomInfo enrichment request failed for {lead.email}: {exc}"
            )

        contacts = data.get("data", [])
        if not contacts:
            logger.info("No ZoomInfo data found for %s", lead.email)
            return EnrichmentData()

        contact = contacts[0]
        company = contact.get("company", {})

        return EnrichmentData(
            company_revenue=str(company.get("revenue", "")),
            employee_count=company.get("employeeCount"),
            industry=str(company.get("industry", "")),
            company_website=str(company.get("website", "")),
            direct_phone=str(contact.get("directPhoneNumber", "")),
        )

    def enrich_leads(self, leads: list[Lead]) -> list[tuple[Lead, EnrichmentData]]:
        results: list[tuple[Lead, EnrichmentData]] = []
        for lead in leads:
            try:
                enrichment = self.enrich_lead(lead)
                results.append((lead, enrichment))
            except ZoomInfoAgentError:
                logger.warning(
                    "Failed to enrich lead %s, skipping", lead.email
                )
        return results
