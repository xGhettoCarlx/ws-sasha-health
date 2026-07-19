"""
Inbox schema — cross-agent message inbox (inbox.md).

Captures messages and forwarded documents from other Hermes agents
that relate to health topics, with OCR status and extraction metadata.
"""

from typing import Literal, Optional

from pydantic import Field

from .common import CommonBase, TrustTier

OcrStatus = Literal["pending", "processing", "completed", "failed"]


class InboxItemSchema(CommonBase):
    """A single inbox item — usually a forwarded health message or document."""

    filename: str = Field(
        description="Original filename of the forwarded document",
    )
    original_path: Optional[str] = Field(
        default=None,
        description="Full path to the original file in Hermes storage",
    )
    ocr_status: OcrStatus = Field(
        default="pending",
        description="OCR processing status",
    )
    extracted_data: dict = Field(
        default_factory=dict,
        description="Key-value data extracted from the document",
    )
    created_at: str = Field(
        description="ISO-8601 timestamp when the item was created",
    )
    processed: bool = Field(
        default=False,
        description="Whether this item has been processed",
    )
    source_tier: TrustTier = Field(
        default="unverified",
        description="Trust tier of the source agent",
    )
