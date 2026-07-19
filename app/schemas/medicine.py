"""
Medicine schema — medication tracker (лекарства.md).

Captures each medication with dosage, frequency, remaining stock,
and prescription expiry for auto-reminders.
"""

from typing import Optional

from pydantic import Field

from .common import CommonBase


class MedicineSchema(CommonBase):
    """A single medication entry."""

    name: str = Field(description="Medication name")
    dose: str = Field(description="Dosage (e.g. '200 мг', '5 мг')")
    frequency: str = Field(description="How often taken (e.g. 'на ночь', 'редко')")
    stock: Optional[str] = Field(
        default=None,
        description="Remaining stock (e.g. '60 таб', '10 таб')",
    )
    prescription_expiry: Optional[str] = Field(
        default=None,
        description="ISO date when prescription expires",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Extra info (regularity, reason, etc.)",
    )
    is_daily: bool = Field(
        default=False,
        description="Whether this medication is taken daily",
    )
    daily_dose: Optional[int] = Field(
        default=None,
        description="Daily dosage count (e.g. pills per day)",
    )
    days_left: Optional[int] = Field(
        default=None,
        description="Estimated days of remaining stock",
    )
