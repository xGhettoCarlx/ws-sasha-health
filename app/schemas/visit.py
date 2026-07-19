"""
Visit schema — doctor visit record (Терапевт/*.md, УЗИ/*.md etc.).

Captures a single medical appointment: date, physician, institution,
subjective complaints, objective findings, diagnosis, and recommendations.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import CommonBase

VisitStatus = Literal[
    "planned",
    "pending",
    "completed",
    "cancelled",
]


class DiagnosticFinding(CommonBase):
    """A single objective measurement or finding during a visit."""

    parameter: str = Field(description="Parameter name (e.g. 'АД', 'ЧСС', 'Вес')")
    recorded_value: str = Field(description="Value recorded by doctor")
    real_value: Optional[str] = Field(
        default=None,
        description="Actual value if recorded value is known to be inaccurate",
    )
    reliability: str = Field(
        default="unknown",
        description="Data reliability (✅ / ⚠️ / ❌ / не мерялось)",
    )


class VisitCreate(BaseModel):
    """Payload for creating a new visit record."""

    date: str = Field(description="Visit date (YYYY-MM-DD)")
    time: Optional[str] = Field(
        default=None, description="Appointment time (HH:MM)"
    )
    doctor: str = Field(description="Doctor name and speciality")
    institution: Optional[str] = Field(
        default=None, description="Medical institution"
    )
    purpose: str = Field(description="Reason for the visit")
    status: VisitStatus = Field(
        default="planned", description="Current visit status"
    )
    notes: Optional[str] = Field(
        default=None, description="Additional notes"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags / categories"
    )


class VisitUpdate(BaseModel):
    """Partial update for a visit record — every field is optional."""

    date: Optional[str] = Field(default=None, description="Visit date (YYYY-MM-DD)")
    time: Optional[str] = Field(default=None, description="Appointment time (HH:MM)")
    doctor: Optional[str] = Field(default=None, description="Doctor name and speciality")
    institution: Optional[str] = Field(default=None, description="Medical institution")
    purpose: Optional[str] = Field(default=None, description="Reason for the visit")
    status: Optional[VisitStatus] = Field(default=None, description="Current visit status")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    tags: Optional[list[str]] = Field(default=None, description="Tags / categories")


class VisitSchema(CommonBase):
    """A single medical visit record."""

    doctor: str = Field(
        description="Doctor name and speciality",
    )
    institution: str = Field(
        description="Medical institution",
    )
    complaint: Optional[str] = Field(
        default=None,
        description="Patient's chief complaint (Жалобы)",
    )
    objective_status: Optional[str] = Field(
        default=None,
        description="Objective examination findings (Объективный статус)",
    )
    objective_data: list[DiagnosticFinding] = Field(
        default_factory=list,
        description="Measured vitals / findings with reliability markers",
    )
    diagnosis: Optional[str] = Field(
        default=None,
        description="Established diagnosis(es)",
    )
    recommendations: Optional[str] = Field(
        default=None,
        description="Doctor recommendations",
    )
    conclusion: Optional[str] = Field(
        default=None,
        description="Summary / commentary on the visit",
    )
