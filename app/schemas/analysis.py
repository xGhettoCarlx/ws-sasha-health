"""
Analysis schema — lab / instrument test results (Анализы/, УЗИ/, МРТ-КТ/).

Captures a single test event with institution, equipment, measured
parameters (name/value/unit/reference range), and clinical conclusion.
"""

from typing import Optional

from pydantic import Field

from .common import CommonBase


class ParameterItem(CommonBase):
    """A single measured parameter within a lab analysis."""

    name: str = Field(description="Parameter name (e.g. 'Белок общий', 'Гемоглобин')")
    value: str = Field(description="Measured value with unit (e.g. '76,0 г/л')")
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement (e.g. 'г/л', 'ммоль/л')",
    )
    ref_range: Optional[str] = Field(
        default=None,
        description="Normal reference range (e.g. '65–85', '0–18')",
    )
    flag: Optional[str] = Field(
        default=None,
        description="Status flag (✅ / ⚠️ / 🔴 / —)",
    )


class AnalysisSchema(CommonBase):
    """A single analysis or diagnostic test event."""

    test_name: str = Field(
        description="Test name (e.g. 'Биохимический анализ крови', 'МРТ поясничного отдела')",
    )
    institution: Optional[str] = Field(
        default=None,
        description="Medical institution where the test was performed",
    )
    equipment: Optional[str] = Field(
        default=None,
        description="Equipment used (e.g. 'PHILIPS Ingenia S 1.5T')",
    )
    parameters: list[ParameterItem] = Field(
        default_factory=list,
        description="All measured parameters from this test",
    )
    conclusion: Optional[str] = Field(
        default=None,
        description="Clinical conclusion / interpretation",
    )
    recommendations: Optional[str] = Field(
        default=None,
        description="Doctor recommendations following this test",
    )
