"""
Fluorography schema — FLG exam history (флюорография.md).

Tracks past fluorography exams (date, reference number, result, institution)
and the next scheduled due date.
"""

from typing import Optional

from pydantic import BaseModel, Field


class FluorographyRecord(BaseModel):
    """A single fluorography exam entry — flat fields from frontmatter history."""

    date: str = Field(description="ISO-8601 date of the exam")
    number: str = Field(description="Exam reference / accession number")
    result: str = Field(description="Clinical result (e.g. 'Отрицательный (норма) ✅')")
    institution: str = Field(description="Medical institution where the exam was performed")


class FluorographySchema(BaseModel):
    """Fluorography overview — exam history and next due date."""

    history: list[FluorographyRecord] = Field(
        default_factory=list,
        description="All past fluorography exam entries",
    )
    next_due: Optional[str] = Field(
        default=None,
        description="ISO-8601 date of the next planned fluorography",
    )
