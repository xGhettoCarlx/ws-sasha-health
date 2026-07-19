"""
Hermes .md migration — seed data from old plain markdown to YAML frontmatter format.

Scans /Users/sashak/Hermes/Саша/Боты/sasha-health/ for all .md files,
maps old markdown structure to new YAML frontmatter format via Pydantic schemas,
copies JPG/PDF originals to bundle dirs, and converts emoji tags to trust_tier enum.

Usage:
    python -m app.seed                     # scan Hermes dir, seed to data/seeds/
    python -m app.seed --dry-run           # preview only, no writes
    python -m app.seed --source <dir>      # custom source directory
    python -m app.seed --target <dir>      # custom target directory
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from app.schemas import (
    AnalysisSchema,
    InboxItemSchema,
    InsuranceSchema,
    MedicineSchema,
    ParameterItem,
    ScheduleSchema,
    StrategySchema,
    StrategyStep,
    TrustTier,
    VisitItem,
    VisitSchema,
    VisitStatus,
    to_frontmatter,
)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

DEFAULT_SOURCE = Path("/Users/sashak/Hermes/Саша/Боты/sasha-health")
DEFAULT_TARGET = Path(__file__).resolve().parent.parent / "data" / "seeds"

MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".pdf", ".png"}

# Emoji-to-trust-tier mapping
EMOJI_TRUST_MAP: dict[str, TrustTier] = {
    "✅": "trusted",
    "🟢": "verified",
    "🔴": "unverified",
    "⚠️": "unverified",
    "⚠": "unverified",
    "❌": "unverified",
}

# Directory to schema type mapping
DIR_SCHEMA_MAP: dict[str, str] = {
    "Терапевт": "visit",
    "Анализы": "analysis",
    "УЗИ": "analysis",
    "МРТ-КТ": "analysis",
    "Стоматология": "visit",
}

# Root-level files that map to specific schemas
ROOT_FILE_SCHEMA: dict[str, str] = {
    "лекарства.md": "medicine_list",
    "страховка.md": "insurance",
    "стратегия.md": "strategy",
    "расписание.md": "schedule",
    "inbox.md": "inbox",
    "флюорография.md": "analysis",
    "мед-протокол.md": "protocol",
    "для_терапевта_поликлиника.md": "protocol",
    "проект-5-врачебный-мини-апп.md": "protocol",
}


# ──────────────────────────────────────────────────────────────────────
# Markdown document model
# ──────────────────────────────────────────────────────────────────────


@dataclass
class MarkdownSection:
    """A markdown heading with its level, title, and body text."""

    level: int
    title: str
    body: str
    subsections: list[MarkdownSection] = field(default_factory=list)


@dataclass
class MarkdownDoc:
    """Parsed markdown document with sections, tables, and metadata."""

    path: Path
    raw: str
    sections: list[MarkdownSection] = field(default_factory=list)
    kv_pairs: dict[str, str] = field(default_factory=dict)
    tables: list[list[dict[str, str]]] = field(default_factory=list)
    emoji_tags: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        """First H1 heading, stripped of emoji prefix."""
        for s in self.sections:
            if s.level == 1:
                return _strip_emoji_prefix(s.title)
        return self.path.stem

    @property
    def date(self) -> str | None:
        """Extract ISO date from filename or content."""
        m = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", self.path.stem)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return None

    def find_section(self, title: str, level: int = 2) -> MarkdownSection | None:
        """Find a section by title (case-insensitive prefix match)."""
        title_lower = title.lower()
        for s in self.sections:
            if s.level == level and s.title.lower().startswith(title_lower):
                return s
            for sub in s.subsections:
                if sub.title.lower().startswith(title_lower):
                    return sub
        return None

    def iter_subsections(self, parent_title: str) -> list[MarkdownSection]:
        """Return subsections under a given parent H2."""
        parent = self.find_section(parent_title)
        if parent:
            return parent.subsections
        return []


# ──────────────────────────────────────────────────────────────────────
# Markdown parsing helpers
# ──────────────────────────────────────────────────────────────────────

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_KV_RE = re.compile(r"^\*\*(.+?):\*\*\s+(.+)$", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\|[-| :]+\|\s*$", re.MULTILINE)
_EMOJI_TRUST_PATTERNS: list[str] = list(EMOJI_TRUST_MAP.keys())


def _is_emoji_char(ch: str) -> bool:
    """Check if a character is an emoji or symbol."""
    cp = ord(ch)
    return (
        0x1F000 <= cp <= 0x1FAFF  # Emoticons, symbols, etc.
        or 0x2600 <= cp <= 0x27BF  # Misc symbols
        or 0x2300 <= cp <= 0x23FF  # Misc technical
        or 0xFE0F <= cp <= 0xFE0F  # Variation selector
        or cp == 0x200D           # ZWJ
        or 0x2702 <= cp <= 0x27B0  # Dingbats
        or cp == 0x2B50           # Star
        or cp == 0x2764           # Heart
    )


def _strip_emoji_prefix(text: str) -> str:
    """Remove leading emoji(s) from a title."""
    stripped = text.strip()
    while stripped and _is_emoji_char(stripped[0]):
        stripped = stripped[1:]
        while stripped and _is_emoji_char(stripped[0]):
            stripped = stripped[1:]
        stripped = stripped.lstrip()
    return stripped


def _detect_emoji_trust(text: str) -> TrustTier | None:
    """Detect trust tier from emoji markers in text."""
    for emoji, tier in EMOJI_TRUST_MAP.items():
        if emoji in text:
            return tier
    return None


def _best_trust_tier(tiers: list[TrustTier | None]) -> TrustTier:
    """Best tier from a list. If mixed, prefer the strongest found."""
    for t in tiers:
        if t == "trusted":
            return "trusted"
    for t in tiers:
        if t == "verified":
            return "verified"
    return "unverified"


def _extract_iso_date(text: str) -> str | None:
    """Extract ISO date (YYYY-MM-DD) from text."""
    m = re.search(r"(\d{4})[-.](\d{2})[-.](\d{2})", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def parse_markdown(path: Path) -> MarkdownDoc:
    """Parse a markdown file into a structured MarkdownDoc."""
    raw = path.read_text(encoding="utf-8")

    # Extract key-value pairs (bold **Key:** value)
    kv_pairs: dict[str, str] = {}
    for m in _KV_RE.finditer(raw):
        kv_pairs[m.group(1).strip().lower()] = m.group(2).strip()

    # Extract emoji tags (known trust-tier emojis found in text)
    emoji_tags: list[str] = []
    for emoji in _EMOJI_TRUST_PATTERNS:
        if emoji in raw:
            emoji_tags.append(emoji)

    # Parse sections (heading hierarchy)
    sections = _parse_sections(raw)

    # Parse tables
    tables = _parse_tables(raw)

    return MarkdownDoc(
        path=path,
        raw=raw,
        sections=sections,
        kv_pairs=kv_pairs,
        tables=tables,
        emoji_tags=emoji_tags,
    )


def _parse_sections(text: str) -> list[MarkdownSection]:
    """Parse markdown heading hierarchy into a tree of MarkdownSection."""
    lines = text.split("\n")
    root: list[MarkdownSection] = []
    stack: list[MarkdownSection] = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if not m:
            continue
        level = len(line) - len(line.lstrip("#"))
        title = m.group(1).strip()
        section = MarkdownSection(level=level, title=title, body="")

        # Pop stack until we find a parent at a lower level
        while stack and stack[-1].level >= level:
            stack.pop()

        if stack:
            stack[-1].subsections.append(section)
        else:
            root.append(section)

        stack.append(section)

    # Fill in body text for each section
    _fill_section_bodies(root, _section_body_map(text))
    return root


def _section_body_map(text: str) -> dict[str, str]:
    """Map each heading to its body text."""
    result: dict[str, str] = {}
    lines = text.split("\n")
    current_heading: str | None = None
    current_body: list[str] = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            if current_heading is not None:
                result[current_heading] = "\n".join(current_body).strip()
            current_heading = m.group(1).strip()
            current_body = []
        elif current_heading is not None:
            current_body.append(line)

    if current_heading is not None:
        result[current_heading] = "\n".join(current_body).strip()

    return result


def _fill_section_bodies(
    sections: list[MarkdownSection],
    body_map: dict[str, str],
) -> None:
    """Recursively fill body text for sections."""
    for s in sections:
        s.body = body_map.get(s.title, "")
        _fill_section_bodies(s.subsections, body_map)


def _parse_tables(text: str) -> list[list[dict[str, str]]]:
    """Parse all markdown tables in text. Returns list of tables, each as list of row dicts."""
    tables: list[list[dict[str, str]]] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        table, new_i = _try_parse_table(lines, i)
        if table:
            tables.append(table)
            i = new_i
        else:
            i += 1
    return tables


def _try_parse_table(
    lines: list[str],
    start: int,
) -> tuple[list[dict[str, str]] | None, int]:
    """Try to parse a markdown table starting at line index start."""
    if start >= len(lines):
        return None, start

    # Find header row
    header_line = lines[start].strip()
    if not header_line.startswith("|") or not header_line.endswith("|"):
        return None, start

    # Must have separator on next line
    if start + 1 >= len(lines):
        return None, start
    sep_line = lines[start + 1].strip()
    if not _TABLE_SEP_RE.match(sep_line):
        return None, start

    # Parse headers
    headers = [h.strip() for h in header_line.split("|")[1:-1]]

    # Parse rows
    rows: list[dict[str, str]] = []
    i = start + 2
    while i < len(lines):
        row_line = lines[i].strip()
        if not row_line.startswith("|"):
            break
        cells = [c.strip() for c in row_line.split("|")[1:-1]]
        # Pad cells to match header count
        while len(cells) < len(headers):
            cells.append("")
        row_dict = dict(zip(headers, cells[:len(headers)]))
        rows.append(row_dict)
        i += 1

    if not rows:
        return None, i

    return rows, i


# ──────────────────────────────────────────────────────────────────────
# File classification
# ──────────────────────────────────────────────────────────────────────


def _classify_file(filepath: Path, source_root: Path) -> str:
    """Determine the schema type for a given .md file.

    Returns one of: 'visit', 'analysis', 'medicine_list', 'insurance',
    'strategy', 'schedule', 'inbox', 'protocol', 'history', 'skip'.
    """
    rel = filepath.relative_to(source_root)
    parts = rel.parts

    # Root-level files with known schema mapping
    if len(parts) == 1 and parts[0] in ROOT_FILE_SCHEMA:
        return ROOT_FILE_SCHEMA[parts[0]]

    # история.md in any subfolder — summary/changelog
    if parts[-1] == "история.md":
        return "history"

    # Subfolder files — classify by parent directory
    if len(parts) == 2 and parts[0] in DIR_SCHEMA_MAP and parts[1].endswith(".md"):
        return DIR_SCHEMA_MAP[parts[0]]

    return "skip"


# ──────────────────────────────────────────────────────────────────────
# Trust tier extraction
# ──────────────────────────────────────────────────────────────────────


def _extract_trust_tier(doc: MarkdownDoc) -> TrustTier:
    """Extract trust tier from emoji tags found in the document."""
    tiers: list[TrustTier | None] = []
    for tag in doc.emoji_tags:
        if tag in EMOJI_TRUST_MAP:
            tiers.append(EMOJI_TRUST_MAP[tag])
    # Also check section titles for emoji
    for s in doc.sections:
        t = _detect_emoji_trust(s.title)
        if t:
            tiers.append(t)
    return _best_trust_tier(tiers)


# ──────────────────────────────────────────────────────────────────────
# Schema-specific parsers
# ──────────────────────────────────────────────────────────────────────


def _parse_visit(doc: MarkdownDoc, source_root: Path) -> VisitSchema:
    """Parse a visit record (Терапевт/YYYY-MM-DD_*.md)."""
    trust = _extract_trust_tier(doc)
    date = doc.date or "unknown"

    # Extract institution and doctor from key-value pairs
    institution = doc.kv_pairs.get("учреждение", "")
    doctor = doc.kv_pairs.get("врач", "")

    # If not in KV pairs, try to extract from first H1
    if not doctor:
        doctor = doc.title

    # Extract complaint from Жалобы section
    complaint = None
    sec = doc.find_section("жалоб")
    if sec and sec.body:
        complaint = sec.body.strip().lstrip(">").strip()

    # Extract objective status
    objective_status = None
    sec = doc.find_section("объективный статус")
    if sec and sec.body:
        objective_status = sec.body.strip().lstrip(">").strip()

    # Extract diagnosis
    diagnosis = None
    sec = doc.find_section("диагноз")
    if sec and sec.body:
        diagnosis = sec.body.strip()

    # Extract recommendations
    recommendations = None
    sec = doc.find_section("рекомендации")
    if sec and sec.body:
        recommendations = sec.body.strip().lstrip(">").strip()

    # Extract conclusion/commentary
    conclusion = None
    sec = doc.find_section("комментарий")
    if sec and sec.body:
        conclusion = sec.body.strip()
    if not conclusion:
        sec = doc.find_section("резюме")
        if sec and sec.body:
            conclusion = sec.body.strip()
    if not conclusion:
        sec = doc.find_section("вывод")
        if sec and sec.body:
            conclusion = sec.body.strip()

    return VisitSchema(
        id=doc.path.stem,
        trust_tier=trust,
        tags=doc.emoji_tags,
        date=date,
        source="Hermes migration",
        content=doc.raw,
        doctor=doctor,
        institution=institution,
        complaint=complaint,
        objective_status=objective_status,
        diagnosis=diagnosis,
        recommendations=recommendations,
        conclusion=conclusion,
    )


def _lower_keys(d: dict[str, str]) -> dict[str, str]:
    """Normalize dict keys to lowercase for case-insensitive lookup."""
    return {k.lower(): v for k, v in d.items()}


def _parse_analysis(doc: MarkdownDoc, source_root: Path) -> AnalysisSchema:
    """Parse an analysis record (Анализы/YYYY-MM-DD_*.md, УЗИ/*.md, etc.)."""
    trust = _extract_trust_tier(doc)
    date = doc.date or "unknown"

    # Test name from title
    test_name = doc.title

    # Institution
    institution = doc.kv_pairs.get("учреждение", None)
    if not institution:
        institution = doc.kv_pairs.get("лаборатория", None)

    # Equipment (for МРТ/КТ/УЗИ)
    equipment = doc.kv_pairs.get("оборудование", None)

    # Parse parameters from table in Результаты section
    parameters: list[ParameterItem] = []
    results_sec = doc.find_section("результаты")
    if results_sec:
        for table in _parse_tables(results_sec.body if results_sec.body else doc.raw):
            for row in table:
                row_lower = _lower_keys(row)
                name = row_lower.get("показатель", "")
                value = row_lower.get("результат", "")
                unit = None
                ref_range = row_lower.get("норма", None)
                flag = row_lower.get("флаг", None)

                if not name:
                    continue

                param = ParameterItem(
                    name=name,
                    value=value,
                    unit=unit,
                    ref_range=ref_range,
                    flag=flag,
                    trust_tier=trust,
                    date=date,
                )
                parameters.append(param)

    # Conclusion — may be "Заключение", "Вывод", or "Резюме"
    conclusion = None
    for kw in ("заключение", "вывод", "резюме"):
        sec = doc.find_section(kw)
        if sec and sec.body:
            conclusion = sec.body.strip()
            break

    # Recommendations
    recommendations = None
    sec = doc.find_section("рекомендации")
    if sec and sec.body:
        recommendations = sec.body.strip()

    return AnalysisSchema(
        id=doc.path.stem,
        trust_tier=trust,
        tags=doc.emoji_tags,
        date=date,
        source="Hermes migration",
        content=doc.raw,
        test_name=test_name,
        institution=institution,
        equipment=equipment,
        parameters=parameters,
        conclusion=conclusion,
        recommendations=recommendations,
    )


def _parse_medicine_list(doc: MarkdownDoc, source_root: Path) -> list[MedicineSchema]:
    """Parse лекарства.md — medication list."""
    trust = _extract_trust_tier(doc)
    medications: list[MedicineSchema] = []

    # Try to parse table data
    for table in doc.tables:
        for row in table:
            name = row.get("название", "").strip("* ")
            dose = row.get("доза", "")
            frequency = row.get("кратность", "")
            stock = row.get("остаток", None)
            prescription_expiry = row.get("рецепт до", None)

            if not name or not dose:
                continue

            med = MedicineSchema(
                name=name,
                dose=dose,
                frequency=frequency or "по требованию",
                stock=stock,
                prescription_expiry=prescription_expiry,
                trust_tier=trust,
                date=doc.date or "unknown",
                source="Hermes migration",
                content=doc.raw,
            )
            medications.append(med)

    return medications


def _parse_strategy(doc: MarkdownDoc, source_root: Path) -> StrategySchema:
    """Parse стратегия.md — health strategy."""
    trust = _extract_trust_tier(doc)
    date = doc.date or "unknown"

    # Extract updated date from content
    updated = date
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", doc.raw)
    if m:
        updated = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    steps: list[StrategyStep] = []

    # Look for H2 sections — either at top level or nested under an H1
    h2_sections: list[MarkdownSection] = []
    for section in doc.sections:
        if section.level == 2:
            h2_sections.append(section)
        h2_sections.extend(s for s in section.subsections if s.level == 2)

    for section in h2_sections:
        section_name = _strip_emoji_prefix(section.title)

        # Parse H3 subsections as steps
        for i, sub in enumerate(section.subsections):
            step_title = _strip_emoji_prefix(sub.title)
            body = sub.body

            # Extract fields from body
            symptom = None
            reason = None
            preparation = None
            what_to_say = None

            for line in body.split("\n"):
                line = line.strip()
                if line.startswith("**Симптом:**") or line.startswith("**С чем:**"):
                    symptom = line.split(":", 1)[1].strip().lstrip("*").strip()
                elif line.startswith("**Почему:**"):
                    reason = line.split(":", 1)[1].strip().lstrip("*").strip()
                elif line.startswith("**Подготовка:**"):
                    preparation = line.split(":", 1)[1].strip().lstrip("*").strip()
                elif line.startswith("**Что сказать:**"):
                    what_to_say = line.split(":", 1)[1].strip().lstrip("*").strip()

            step = StrategyStep(
                section=section_name,
                priority=i + 1,
                symptom=symptom or step_title,
                reason=reason,
                preparation=preparation,
                what_to_say=what_to_say,
                trust_tier=trust,
                date=date,
            )
            steps.append(step)

    return StrategySchema(
        id=doc.path.stem,
        trust_tier=trust,
        tags=doc.emoji_tags,
        date=date,
        source="Hermes migration",
        content=doc.raw,
        title=doc.title,
        steps=steps,
        updated=updated,
    )


def _parse_schedule(doc: MarkdownDoc, source_root: Path) -> ScheduleSchema:
    """Parse расписание.md — visit schedule."""
    trust = _extract_trust_tier(doc)
    date = doc.date or "unknown"

    visits: list[VisitItem] = []
    reminders: list[str] = []

    # Parse visits from table in Ближайшие section
    for table in doc.tables:
        for row in table:
            row_lower = _lower_keys(row)
            visit_date = row_lower.get("дата", "")
            time = row_lower.get("время", None)
            doctor_val = row_lower.get("врач", "")
            institution = row_lower.get("учреждение", None)
            purpose = row_lower.get("цель", "")

            if not doctor_val:
                continue

            # Determine status from content
            status: VisitStatus = "planned"
            if "после страховки" in visit_date.lower() or "ожидание" in visit_date.lower():
                status = "pending"
            if "отменён" in visit_date.lower():
                status = "cancelled"

            # Best-effort date extraction
            visit_iso = _extract_iso_date(visit_date) or date

            visit = VisitItem(
                date=visit_iso,
                time=time,
                doctor=doctor_val.strip("* ").replace("**", ""),
                institution=institution,
                purpose=purpose,
                status=status,
                trust_tier=trust,
            )
            visits.append(visit)

    # Parse reminders from Напоминания section
    sec = doc.find_section("напоминания")
    if sec:
        for line in sec.body.split("\n"):
            line = line.strip()
            if line.startswith("-") and len(line) > 2:
                reminders.append(line.lstrip("- 🔔").strip())

    return ScheduleSchema(
        id=doc.path.stem,
        trust_tier=trust,
        tags=doc.emoji_tags,
        date=date,
        source="Hermes migration",
        content=doc.raw,
        visits=visits,
        reminders=reminders,
    )


def _parse_insurance(doc: MarkdownDoc, source_root: Path) -> InsuranceSchema:
    """Parse страховка.md — insurance record."""
    return InsuranceSchema(
        id=doc.path.stem,
        trust_tier="unverified",
        tags=doc.emoji_tags,
        date=doc.date or "unknown",
        source="Hermes migration",
        content=doc.raw,
    )


def _parse_inbox(doc: MarkdownDoc, source_root: Path) -> list[InboxItemSchema]:
    """Parse inbox.md — cross-agent inbox."""
    return []  # inbox.md is currently empty


# ──────────────────────────────────────────────────────────────────────
# Attachment discovery
# ──────────────────────────────────────────────────────────────────────


def _find_attachments(md_path: Path, source_root: Path) -> list[Path]:
    """Find all media files (JPG/PDF) associated with an .md file.

    Matches on: same directory, same stem prefix (before _).
    For example: 2026-06-10_осмотр_Кабаев.md matches
        2026-06-10_осмотр_Кабаев.jpg
        2026-06-10_для_врача_Кабаев.pdf (shared date prefix)
    """
    md_dir = md_path.parent
    md_stem = md_path.stem

    attachments: list[Path] = []

    # Exact stem match (same filename, different extension)
    for ext in MEDIA_EXTENSIONS:
        candidate = md_dir / f"{md_stem}{ext}"
        if candidate.exists():
            attachments.append(candidate)

    # Prefix match for related files (e.g., _стр1.jpg, _v2.pdf)
    for f in md_dir.iterdir():
        if f.suffix.lower() in MEDIA_EXTENSIONS:
            if f.stem.startswith(md_stem.split("_")[0]) and f not in attachments:
                # Only if shares at least the date prefix (YYYY-MM-DD)
                date_prefix = md_stem[:10] if len(md_stem) >= 10 else md_stem
                if f.stem.startswith(date_prefix):
                    attachments.append(f)

    return sorted(set(attachments))


# ──────────────────────────────────────────────────────────────────────
# Output writer
# ──────────────────────────────────────────────────────────────────────


def _write_frontmatter_md(
    schema: Any,
    output_root: Path,
    source_path: Path,
    source_root: Path,
) -> Path:
    """Write a single seeded .md file with YAML frontmatter.

    Returns the path of the written .md file.
    """
    rel = source_path.relative_to(source_root)
    # Preserve directory structure under output root
    out_path = output_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert schema to frontmatter dict
    fm_dict = to_frontmatter(schema)

    # Remove 'content' from frontmatter (write it as body instead)
    body = fm_dict.pop("content", "") if isinstance(fm_dict, dict) else ""

    # Build YAML frontmatter + markdown body
    yaml_str = yaml.dump(
        fm_dict,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    output = f"---\n{yaml_str}---\n\n{body}"

    out_path.write_text(output, encoding="utf-8")
    return out_path


def _copy_attachments(
    attachments: list[Path],
    md_path: Path,
    output_root: Path,
    source_root: Path,
) -> list[Path]:
    """Copy associated JPG/PDF files to a bundle directory next to the .md file."""
    if not attachments:
        return []

    rel = md_path.relative_to(source_root)
    bundle_dir = output_root / rel.parent / f"{md_path.stem}"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for att in attachments:
        dest = bundle_dir / att.name
        shutil.copy2(att, dest)
        copied.append(dest)

    return copied


# ──────────────────────────────────────────────────────────────────────
# Main seeding logic
# ──────────────────────────────────────────────────────────────────────

# Dispatch table: schema_type → parser function
PARSER_MAP: dict[str, Callable] = {
    "visit": _parse_visit,
    "analysis": _parse_analysis,
    "medicine_list": _parse_medicine_list,
    "insurance": _parse_insurance,
    "strategy": _parse_strategy,
    "schedule": _parse_schedule,
    "inbox": _parse_inbox,
}


def _seed_one(
    md_path: Path,
    source_root: Path,
    output_root: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Seed a single .md file. Returns a result dict."""
    rel = str(md_path.relative_to(source_root))
    stype = _classify_file(md_path, source_root)

    result: dict[str, Any] = {
        "path": rel,
        "type": stype,
        "status": "skipped",
        "written_files": [],
        "attachments_copied": 0,
    }

    if stype == "skip":
        return result

    if stype == "history":
        doc = parse_markdown(md_path)
        from app.schemas.common import CommonBase

        schema = CommonBase(
            id=md_path.stem,
            trust_tier=_extract_trust_tier(doc),
            tags=doc.emoji_tags,
            date=doc.date or "unknown",
            source="Hermes migration (history)",
            content=doc.raw,
        )
        schemas = [schema]
    elif stype == "protocol":
        doc = parse_markdown(md_path)
        from app.schemas.common import CommonBase

        schema = CommonBase(
            id=md_path.stem,
            trust_tier="verified",
            tags=doc.emoji_tags,
            date=doc.date or "unknown",
            source="Hermes migration (protocol)",
            content=doc.raw,
        )
        schemas = [schema]
    elif stype in PARSER_MAP:
        doc = parse_markdown(md_path)
        parsed = PARSER_MAP[stype](doc, source_root)
        schemas = parsed if isinstance(parsed, list) else [parsed]
    else:
        return result

    if dry_run:
        result["status"] = "dry_run"
        result["preview"] = to_frontmatter(schemas[0]) if schemas else {}
        return result

    try:
        for schema in schemas:
            written = _write_frontmatter_md(schema, output_root, md_path, source_root)
            result["written_files"].append(str(written))

        # Copy attachments
        attachments = _find_attachments(md_path, source_root)
        if attachments:
            copied = _copy_attachments(attachments, md_path, output_root, source_root)
            result["attachments_copied"] = len(copied)
            result["written_files"].extend(str(c) for c in copied)

        result["status"] = "seeded"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def seed(
    source: Path | None = None,
    target: Path | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Main entry point: scan source dir, seed all .md files to target dir.

    Args:
        source: Root directory containing .md files (default: Hermes sasha-health/).
        target: Output directory for seeded files (default: data/seeds/).
        dry_run: If True, parse only — no writes.

    Returns:
        List of result dicts, one per .md file processed.
    """
    src = Path(source) if source else DEFAULT_SOURCE
    out = Path(target) if target else DEFAULT_TARGET

    if not src.exists():
        raise FileNotFoundError(f"Source directory not found: {src}")

    out.mkdir(parents=True, exist_ok=True)

    # Collect all .md files (skip .DS_Store, skip история.md — handled by seed_one)
    md_files: list[Path] = []
    for md in sorted(src.rglob("*.md")):
        if md.name == ".DS_Store":
            continue
        if "__pycache__" in md.parts:
            continue
        md_files.append(md)

    results: list[dict[str, Any]] = []
    stats = {"total": len(md_files), "seeded": 0, "skipped": 0, "errors": 0}

    for md_path in md_files:
        r = _seed_one(md_path, src, out, dry_run=dry_run)
        results.append(r)
        if r["status"] == "seeded":
            stats["seeded"] += 1
        elif r["status"] in ("skipped", "history", "protocol"):
            stats["skipped"] += 1
        elif r["status"] == "error":
            stats["errors"] += 1

    # Print summary
    print(f"Source: {src}")
    print(f"Target: {out}")
    print(f"Total .md files: {stats['total']}")
    print(f"  Seeded: {stats['seeded']}")
    print(f"  Skipped (history/protocol): {stats['skipped']}")
    if stats["errors"]:
        print(f"  Errors: {stats['errors']}")
        for r in results:
            if r["status"] == "error":
                print(f"    - {r['path']}: {r.get('error', 'unknown')}")

    return results


# ──────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for `python -m app.seed`."""
    parser = argparse.ArgumentParser(
        description="Seed Hermes .md files to YAML frontmatter format.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Source directory (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"Target directory (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only, do not write any files.",
    )
    args = parser.parse_args(argv)

    results = seed(source=args.source, target=args.target, dry_run=args.dry_run)

    if args.dry_run:
        print("\n--- Dry-run preview (first 5) ---")
        for r in results[:5]:
            print(f"\n[{r['type']}] {r['path']}")
            preview = r.get("preview", {})
            for k, v in preview.items():
                if isinstance(v, str) and len(v) > 80:
                    v = v[:77] + "..."
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main(sys.argv[1:])
