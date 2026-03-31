"""Entry point for the lead orchestrator pipeline."""

from __future__ import annotations

import logging
import sys

import config
from brain import Brain, BrainError
from gmail_agent import GmailAgent, GmailAgentError
from sheets_client import SheetsClient, SheetsClientError
from zoominfo_agent import ZoomInfoAgent, ZoomInfoAgentError

logger = logging.getLogger(__name__)


def main() -> None:
    config.configure_logging()

    try:
        config.validate_required_settings()
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    try:
        sheets = SheetsClient()
        zoominfo = ZoomInfoAgent()
        gmail = GmailAgent()
    except (SheetsClientError, ZoomInfoAgentError, GmailAgentError) as exc:
        logger.error("Failed to initialise services: %s", exc)
        sys.exit(1)

    try:
        brain = Brain(sheets=sheets, zoominfo=zoominfo, gmail=gmail)
        summary = brain.run_pipeline()
        logger.info("Run complete — enriched: %d, contacted: %d",
                     summary["enriched"], summary["contacted"])
    except BrainError as exc:
        logger.error("Pipeline error: %s", exc)
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error during pipeline execution")
        sys.exit(1)


if __name__ == "__main__":
    main()
