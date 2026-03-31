"""Data models for lead management with input validation."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator

_PHONE_PATTERN = re.compile(r"^\+?[\d\s\-().]{7,20}$")


class LeadStatus(str, Enum):
    NEW = "new"
    ENRICHED = "enriched"
    CONTACTED = "contacted"
    REPLIED = "replied"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"


class Lead(BaseModel):
    """Represents a single sales lead."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    company: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=30)
    linkedin_url: str = Field(default="", max_length=500)
    status: LeadStatus = LeadStatus.NEW
    notes: str = Field(default="", max_length=5000)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if v and not _PHONE_PATTERN.match(v):
            raise ValueError("Invalid phone number format")
        return v.strip()

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: str) -> str:
        if v and not v.startswith("https://www.linkedin.com/"):
            raise ValueError("LinkedIn URL must start with https://www.linkedin.com/")
        return v.strip()

    @field_validator("first_name", "last_name", "company", "title")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class EnrichmentData(BaseModel):
    """Additional data retrieved from enrichment sources like ZoomInfo."""

    company_revenue: str = Field(default="", max_length=50)
    employee_count: int | None = Field(default=None, ge=0)
    industry: str = Field(default="", max_length=200)
    company_website: str = Field(default="", max_length=500)
    direct_phone: str = Field(default="", max_length=30)

    @field_validator("direct_phone")
    @classmethod
    def validate_direct_phone(cls, v: str) -> str:
        if v and not _PHONE_PATTERN.match(v):
            raise ValueError("Invalid phone number format")
        return v.strip()
