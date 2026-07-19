"""
Insurance schema — DMS policy tracker (страховка.md).

Tracks multiple insurance policies with coverage limits,
spent amounts, remaining balance, and expiry.
"""

from typing import Optional

from pydantic import Field

from .common import CommonBase


class InsurancePolicy(CommonBase):
    """A single insurance policy entry."""

    policy: str = Field(description="Policy name or identifier (e.g. 'Даша (как муж)')")
    sum_insured: float = Field(
        ge=0,
        description="Total coverage amount in BYN",
    )
    spent: float = Field(
        default=0,
        ge=0,
        description="Amount already spent in BYN",
    )
    remaining: float = Field(
        ge=0,
        description="Remaining available funds in BYN",
    )
    expiry: Optional[str] = Field(
        default=None,
        description="ISO date when coverage expires",
    )


class InsuranceSchema(CommonBase):
    """Insurance overview — list of active policies."""

    policies: list[InsurancePolicy] = Field(
        default_factory=list,
        description="All active insurance policies",
    )
