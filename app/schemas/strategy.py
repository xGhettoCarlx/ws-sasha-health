"""
Strategy schema — health action plan (стратегия.md).

Mirrors the structured plan with sections (ДО СТРАХОВКИ, ПО СТРАХОВКЕ, ЕЖЕДНЕВНО)
and actionable steps with context, preparation, and what-to-say guidance.
"""

from typing import Optional

from pydantic import Field

from .common import CommonBase


class StrategyStep(CommonBase):
    """A single actionable step within a strategy section."""

    section: str = Field(
        description="Section heading (e.g. 'ДО СТРАХОВКИ', 'ЕЖЕДНЕВНО')",
    )
    priority: int = Field(
        default=0,
        description="Order within the section (1 = highest)",
    )
    symptom: Optional[str] = Field(
        default=None,
        description="What symptom this step addresses",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Why this step matters",
    )
    preparation: Optional[str] = Field(
        default=None,
        description="What to prepare before doing this step",
    )
    what_to_say: Optional[str] = Field(
        default=None,
        description="Suggested phrasing for the doctor visit",
    )


class StrategySchema(CommonBase):
    """Overall health strategy — sections of ordered steps."""

    title: str = Field(description="Strategy title (e.g. 'Стратегия здоровья — июнь 2026')")
    steps: list[StrategyStep] = Field(
        default_factory=list,
        description="All actionable steps grouped by section",
    )
    updated: str = Field(
        description="ISO date when the strategy was last revised",
    )
