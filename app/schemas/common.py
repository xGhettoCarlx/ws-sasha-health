"""
Common base model and shared types for all health .md schemas.

Trust tiers map to the Hermes emoji-based system:
    - unverified  ← 🔴 / ⚠️ (Grok-only, needs Gemini check)
    - verified    ← 🟢 (Gemini-verified or trusted source)
    - trusted     ← ✅ (lab equipment, official portal)
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

TrustTier = Literal["unverified", "verified", "trusted"]


class CommonBase(BaseModel):
    """Base model inherited by every .md file schema.

    Fields mirror the YAML frontmatter that prefixes each health markdown file.
    """

    id: Optional[str] = Field(
        default=None,
        description="Unique identifier (e.g. UUID or filename stem)",
    )
    trust_tier: TrustTier = Field(
        description="Data reliability level — mirrors Hermes emoji trust system",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags / categories (e.g. emoji section headers)",
    )
    date: str = Field(
        description="ISO-8601 date string (YYYY-MM-DD) for the record",
    )
    source: Optional[str] = Field(
        default=None,
        description="Origin description (e.g. 'электронный кабинет', 'Grok + Gemini')",
    )
    content: Optional[str] = Field(
        default=None,
        description="Raw markdown body after the frontmatter block",
    )
