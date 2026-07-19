"""
Profile schema — patient card (карточка.md).

Maps to the profile block from Hermes documents:
    - полное имя, дата рождения
    - хронические диагнозы со статусом и источником
    - аллергии
"""

from typing import Optional

from pydantic import Field

from .common import CommonBase


class DiagnosisItem(CommonBase):
    """A single diagnosis with status, name, and provenance."""

    status: str = Field(description="Status indicator (🔴/🟡/✅/🟢 etc.)")
    name: str = Field(description="Diagnosis name")
    source: Optional[str] = Field(
        default=None,
        description="Where the diagnosis was recorded",
    )


class ProfileSchema(CommonBase):
    """Patient profile — one per user (Саша)."""

    full_name: str = Field(description="Full name (ФИО)")
    birth_date: str = Field(
        description="Date of birth in ISO format (YYYY-MM-DD)",
    )
    diagnoses: list[DiagnosisItem] = Field(
        default_factory=list,
        description="List of chronic / active diagnoses",
    )
    allergies: list[str] = Field(
        default_factory=list,
        description="Known allergies",
    )
