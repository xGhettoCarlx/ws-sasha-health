"""
Symptom diary schema — daily symptom tracking.

Captures symptom entries with date, description, severity level,
and optional notes for longitudinal tracking.
"""

from typing import Optional

from pydantic import Field

from .common import CommonBase


class SymptomEntry(CommonBase):
    """A single symptom record."""

    symptom: str = Field(description="Symptom name or description")
    severity: int = Field(
        ge=1,
        le=10,
        description="Subjective severity on a 1–10 scale",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional context (triggers, timing, etc.)",
    )


class SymptomDiarySchema(CommonBase):
    """Symptom diary — time-series of symptom records."""

    entries: list[SymptomEntry] = Field(
        default_factory=list,
        description="Symptom entries ordered chronologically",
    )
