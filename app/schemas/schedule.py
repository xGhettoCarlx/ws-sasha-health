"""
Schedule schema — visit calendar (расписание.md).

Captures upcoming and past medical visits with date, time, doctor,
institution, purpose, and status tracking.

Pipeline stages (5-step medical conveyor):
  1 therapist  — направления
  2 specialists — спецы в 1 день → назначения на анализы
  3 labs       — анализы и тесты
  4 final      — финальный приём с результатами
  5 cream      — сливки (процедуры, массажи)
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

PipelineStage = Literal[1, 2, 3, 4, 5]


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
    # ── Pipeline / insurance (HEALTH-MEDICAL-PIPELINE-AND-TIMELINE) ──
    pipeline_stage: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="1=therapist … 5=cream (procedures)",
    )
    specialty: Optional[str] = Field(
        default=None,
        description="Specialty bucket, e.g. Кардиология",
    )
    visit_date: Optional[str] = Field(
        default=None,
        description="Actual appointment date if different from `date` field",
    )
    insurance_warned: bool = Field(
        default=False,
        description="Whether insurance was notified about this upcoming visit",
    )
    pipeline_cycle: Optional[str] = Field(
        default=None,
        description="Optional cycle id to group visits in one conveyor run",
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
