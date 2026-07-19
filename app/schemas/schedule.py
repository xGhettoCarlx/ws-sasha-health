"""
Schedule schema — visit calendar (расписание.md).

Captures upcoming and past medical visits with date, time, doctor,
institution, purpose, and status tracking.
"""

from typing import Literal, Optional

from pydantic import Field

from .common import CommonBase

VisitStatus = Literal[
    "planned",       # 📅 Запланировано
    "pending",      # 🔜 После страховки / ожидание
    "completed",    # ✅ Состоялось
    "cancelled",    # ❌ Отменено
]


class VisitItem(CommonBase):
    """A single medical appointment."""

    time: Optional[str] = Field(
        default=None,
        description="Appointment time (HH:MM or free-text like '—')",
    )
    doctor: str = Field(
        description="Doctor name and speciality (e.g. 'Спицарева О.Е. (кардиолог)')",
    )
    institution: Optional[str] = Field(
        default=None,
        description="Clinic or hospital name",
    )
    purpose: str = Field(
        description="Reason for the visit",
    )
    status: VisitStatus = Field(
        default="planned",
        description="Current visit status",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes / reminders for this visit",
    )


class ScheduleSchema(CommonBase):
    """Visit schedule — list of upcoming and past appointments."""

    visits: list[VisitItem] = Field(
        default_factory=list,
        description="All medical visits ordered chronologically",
    )
    reminders: list[str] = Field(
        default_factory=list,
        description="Reminder notes (e.g. 'Напомнить записаться на ЭКГ')",
    )
