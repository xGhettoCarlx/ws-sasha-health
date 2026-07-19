"""
Frontmatter conversion utilities.

Bidirectional conversion between Pydantic schema instances and
YAML-safe dicts suitable for .md file frontmatter (between --- markers).

Usage:
    # Schema → frontmatter dict
    fm = to_frontmatter(schema_instance)

    # Frontmatter dict + markdown body → schema
    schema = from_frontmatter(ProfileSchema, fm_dict, body_string)
"""

from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def to_frontmatter(schema: BaseModel) -> dict:
    """Convert a Pydantic model instance to a YAML-safe frontmatter dict.

    Strips None-valued fields so YAML output stays clean.
    Nested models are recursively converted to dicts.
    """
    return schema.model_dump(exclude_none=True)


def from_frontmatter(
    model_class: type[T],
    metadata: dict,
    content: str | None = None,
) -> T:
    """Reconstruct a Pydantic model from a frontmatter metadata dict.

    Args:
        model_class: The Pydantic model class to instantiate.
        metadata: Dict of field values parsed from YAML frontmatter.
        content: Optional markdown body to set as the 'content' field.

    Returns:
        An instance of model_class populated with metadata values.
    """
    if content is not None and "content" in model_class.model_fields:
        metadata["content"] = content
    return model_class(**metadata)
