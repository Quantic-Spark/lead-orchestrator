"""Orchestration logic that ties together sheets, enrichment, and outreach."""

from __future__ import annotations

import logging

import config
from gmail_agent import GmailAgent, GmailAgentError
from models import LeadStatus
from sheets_client import SheetsClient, SheetsClientError
from zoominfo_agent import ZoomInfoAgent, ZoomInfoAgentError

logger = logging.getLogger(__name__)

_DEFAULT_SUBJECT = "Quick question, {first_name}"
_DEFAULT_BODY = (
    "Hi {first_name},\n\n"
    "I came across {company} and wanted to reach out.\n\n"
    "Would you be open to a quick chat this week?\n\n"
    "Best regards"
)


class BrainError(Exception):
    """Raised for orchestration-level failures."""


class Brain:
    """High-level orchestrator for the lead pipeline."""

    def __init__(
        self,
        sheets: SheetsClient,
        zoominfo: ZoomInfoAgent,
        gmail: GmailAgent,
    ) -> None:
        self._sheets = sheets
        self._zoominfo = zoominfo
        self._gmail = gmail

    def enrich_new_leads(self) -> int:
        """Enrich all leads with status NEW. Returns count of enriched leads."""
        new_leads = self._sheets.get_leads_by_status(LeadStatus.NEW)
        if not new_leads:
            logger.info("No new leads to enrich")
            return 0

        logger.info("Enriching %d new leads", len(new_leads))
        enriched_count = 0

        for row_index, lead in new_leads:
            try:
                enrichment = self._zoominfo.enrich_lead(lead)
                lead.status = LeadStatus.ENRICHED
                if enrichment.industry:
                    lead.notes = f"Industry: {enrichment.industry}"
                if enrichment.direct_phone and not lead.phone:
                    lead.phone = enrichment.direct_phone

                if config.DRY_RUN:
                    logger.info("[DRY RUN] Would update row %d", row_index)
                else:
                    self._sheets.update_lead_row(row_index, lead)
                enriched_count += 1
            except (ZoomInfoAgentError, SheetsClientError) as exc:
                logger.warning(
                    "Failed to enrich lead %s: %s", lead.email, exc
                )

        logger.info("Enriched %d / %d leads", enriched_count, len(new_leads))
        return enriched_count

    def send_outreach_to_enriched(
        self,
        subject: str = _DEFAULT_SUBJECT,
        body: str = _DEFAULT_BODY,
    ) -> int:
        """Send outreach emails to all ENRICHED leads. Returns sent count."""
        enriched_leads = self._sheets.get_leads_by_status(LeadStatus.ENRICHED)
        if not enriched_leads:
            logger.info("No enriched leads to contact")
            return 0

        logger.info("Sending outreach to %d enriched leads", len(enriched_leads))
        sent_count = 0

        for row_index, lead in enriched_leads:
            try:
                if config.DRY_RUN:
                    logger.info("[DRY RUN] Would email %s", lead.email)
                else:
                    self._gmail.send_outreach(lead, subject, body)

                lead.status = LeadStatus.CONTACTED
                if not config.DRY_RUN:
                    self._sheets.update_lead_row(row_index, lead)
                sent_count += 1
            except (GmailAgentError, SheetsClientError) as exc:
                logger.warning(
                    "Failed to send outreach to %s: %s", lead.email, exc
                )

        logger.info("Sent %d / %d outreach emails", sent_count, len(enriched_leads))
        return sent_count

    def run_pipeline(self) -> dict[str, int]:
        """Run the full pipeline: enrich -> outreach. Returns summary counts."""
        logger.info("Starting lead pipeline%s", " (DRY RUN)" if config.DRY_RUN else "")
        enriched = self.enrich_new_leads()
        contacted = self.send_outreach_to_enriched()
        summary = {"enriched": enriched, "contacted": contacted}
        logger.info("Pipeline complete: %s", summary)
        return summary
