#!/usr/bin/env python3
"""Legacy diagnosis audit + DMS verification plan (LEGACY-DIAGNOSIS-VERIFICATION-PLAN).

Walks ``data/`` (карточка, history, schedule, strategy), collects diagnoses,
marks each as ``unverified`` for insurance re-confirmation, and writes:

  - data/диагнозы_аудит.md
  - data/verification_plan.md  (vs data/страховка.md, pipeline stage 1)

Usage:
  python scripts/audit_diagnoses.py
  python scripts/audit_diagnoses.py --data-dir /path/to/data
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ── Specialty / urgency heuristics for pipeline stage-1 plan ───────────────

# (substring lower, specialist, urgency 1-3, dms notes)
RULES: list[tuple[str, str, int, str]] = [
    (
        "гипертон",
        "Кардиолог (+ терапевт для направления)",
        1,
        "Консультация кардиолога покрывается; Эхо-КГ/Холтер — по направлению; "
        "высоковостребованные >70 BYN — франшиза 40%",
    ),
    (
        "аг ",
        "Кардиолог (+ терапевт)",
        1,
        "ДМС: кардиолог + ЭКГ/Эхо по направлению",
    ),
    (
        "гепатоз",
        "Гастроэнтеролог",
        1,
        "Консультация + УЗИ БП без лимита; ФГДС — в лимите 2 (ФГДС/ФКС суммарно)",
    ),
    (
        "стеатоз",
        "Гастроэнтеролог",
        1,
        "УЗИ + биохимия печени (АлАТ/билирубин) — лаборатории Хеликс/Инвитро/гос.",
    ),
    (
        "жильбер",
        "Гастроэнтеролог / терапевт",
        2,
        "Верификация через биохимию (билирубин); консультация покрывается",
    ),
    (
        "язвенн",
        "Гастроэнтеролог",
        2,
        "ФГДС при необходимости (лимит 2 ФГДС/ФКС за период) — просить по жалобам",
    ),
    (
        "дпк",
        "Гастроэнтеролог",
        2,
        "ФГДС по направлению; контроль ремиссии",
    ),
    (
        "мочекамен",
        "Уролог",
        2,
        "Уролог ≤5 раз за период; УЗИ почек без лимита",
    ),
    (
        "почк",
        "Уролог",
        2,
        "УЗИ + уролог (лимит 5); исключить острый процесс",
    ),
    (
        "жёлчн",
        "Гастроэнтеролог",
        3,
        "УЗИ БП; консультация при симптомах",
    ),
    (
        "желчн",
        "Гастроэнтеролог",
        3,
        "УЗИ БП; консультация при симптомах",
    ),
    (
        "зоб",
        "Эндокринолог",
        2,
        "Консультация + УЗИ ЩЖ; ТТГ/Т3/Т4 — лаборатория по направлению",
    ),
    (
        "щитовид",
        "Эндокринолог",
        2,
        "Эндокринолог + УЗИ + гормоны",
    ),
    (
        "миоп",
        "Офтальмолог",
        3,
        "Консультация офтальмолога покрывается (не из исключений)",
    ),
    (
        "пдс",
        "Офтальмолог",
        3,
        "Контроль глазного дна / ПДС",
    ),
    (
        "геморр",
        "Проктолог / хирург",
        3,
        "Консультация покрывается; малые операции в гос. — по показаниям",
    ),
    (
        "трохантер",
        "Ортопед / травматолог / невролог",
        3,
        "Консультация + УЗИ суставов; массаж/физио — лимиты (10 сеансов массажа)",
    ),
    (
        "щёлкающ",
        "Ортопед / травматолог",
        3,
        "Контроль при боли; физио по направлению",
    ),
    (
        "остеохондр",
        "Невролог",
        2,
        "Консультация; МРТ — 1 раз за период (уже было 2022 — повтор только по показаниям)",
    ),
    (
        "экструз",
        "Невролог",
        2,
        "Невролог; КТ/МРТ — по 1 разу за период, не тратить без симптомов",
    ),
    (
        "стеноз",
        "Невролог",
        2,
        "Невролог; контроль симптоматики",
    ),
    (
        "спондило",
        "Невролог",
        2,
        "Консультация невролога; МРТ повтор — только по симптомам (лимит ×1)",
    ),
    (
        "поджелуд",
        "Гастроэнтеролог",
        2,
        "УЗИ + гастро; лаборатория по направлению",
    ),
    (
        "алat",
        "Гастроэнтеролог",
        2,
        "Биохимия печени — лаборатория покрывается",
    ),
    (
        "алат",
        "Гастроэнтеролог",
        2,
        "Биохимия печени — лаборатория покрывается",
    ),
    (
        "alt",
        "Гастроэнтеролог",
        2,
        "Биохимия печени — лаборатория покрывается",
    ),
    (
        "билируб",
        "Гастроэнтеролог / терапевт",
        2,
        "Биохимия (фракции билирубина) — покрывается",
    ),
    (
        "триглиц",
        "Кардиолог / терапевт",
        2,
        "Липидограмма — лаборатория; связь с АГ",
    ),
    (
        "холестер",
        "Кардиолог / терапевт",
        2,
        "Липидограмма — лаборатория",
    ),
]

URGENCY_LABEL = {1: "высокая", 2: "средняя", 3: "низкая / планово"}


@dataclass
class DiagnosisHit:
    name: str
    status: str = ""
    source: str = ""
    date: str = ""
    origin_path: str = ""
    origin_kind: str = "profile"  # profile | history | schedule | strategy
    clinical_trust_tier: str = ""
    verification_status: str = "unverified"  # always for this audit
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
        return re.sub(r"\s+", " ", self.name.strip().lower())


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_md(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, parts[2]


def _collect_from_profile(data_dir: Path) -> list[DiagnosisHit]:
    path = data_dir / "карточка.md"
    if not path.exists():
        return []
    meta, _ = _read_md(path)
    hits: list[DiagnosisHit] = []
    for d in meta.get("diagnoses") or []:
        if not isinstance(d, dict):
            continue
        name = str(d.get("name") or "").strip()
        if not name:
            continue
        hits.append(
            DiagnosisHit(
                name=name,
                status=str(d.get("status") or ""),
                source=str(d.get("source") or ""),
                date=str(d.get("date") or meta.get("date") or ""),
                origin_path=str(path.relative_to(data_dir)),
                origin_kind="profile",
                clinical_trust_tier=str(d.get("trust_tier") or meta.get("trust_tier") or ""),
                verification_status="unverified",
                notes="Из карточки пациента — требует подтверждения для ДМС/ОМС",
            )
        )
    return hits


def _scan_history_file(path: Path, data_dir: Path) -> list[DiagnosisHit]:
    meta, body = _read_md(path)
    rel = str(path.relative_to(data_dir))
    hits: list[DiagnosisHit] = []
    date_s = str(meta.get("date") or "")

    # Explicit diagnosis field
    diag = meta.get("diagnosis") or meta.get("diagnoses")
    if isinstance(diag, str) and diag.strip():
        # May be semicolon/period separated list
        for part in re.split(r"[.;]\s+", diag.strip()):
            part = part.strip(" .;,-")
            # skip fragments like ", риск 2" or pure codes
            if len(part) < 6 or not re.search(r"[А-Яа-яA-Za-z]{3,}", part):
                continue
            if re.fullmatch(r"[\d\s.,×xX%мм/л]+", part):
                continue
            hits.append(
                DiagnosisHit(
                    name=part,
                    status="",
                    source=str(meta.get("doctor") or meta.get("source") or rel),
                    date=date_s,
                    origin_path=rel,
                    origin_kind="history",
                    clinical_trust_tier=str(meta.get("trust_tier") or ""),
                    verification_status="unverified",
                    notes="Из поля diagnosis в истории",
                )
            )
    elif isinstance(diag, list):
        for item in diag:
            name = item if isinstance(item, str) else (item or {}).get("name")
            if not name:
                continue
            hits.append(
                DiagnosisHit(
                    name=str(name),
                    source=rel,
                    date=date_s,
                    origin_path=rel,
                    origin_kind="history",
                    clinical_trust_tier=str(meta.get("trust_tier") or ""),
                    verification_status="unverified",
                )
            )

    # UZI / MRI parameters with abnormal flags
    for p in meta.get("parameters") or []:
        if not isinstance(p, dict):
            continue
        flag = str(p.get("flag") or "")
        if flag in ("🔴", "🟡", "⚠️", "!") or str(p.get("value") or "").lower() in (
            "подтверждён",
            "подтвержден",
            "подтверждена",
            "подтверждены",
        ):
            pname = str(p.get("name") or "").strip()
            pval = str(p.get("value") or "").strip()
            if not pname:
                continue
            label = f"{pname}" + (f" — {pval}" if pval else "")
            hits.append(
                DiagnosisHit(
                    name=label,
                    status=flag,
                    source=str(meta.get("test_name") or rel),
                    date=date_s or str(p.get("date") or ""),
                    origin_path=rel,
                    origin_kind="history",
                    clinical_trust_tier=str(p.get("trust_tier") or meta.get("trust_tier") or ""),
                    verification_status="unverified",
                    notes="Из параметров обследования (аномалия/подтверждение)",
                )
            )

    # Body line "Диагноз: …"
    for m in re.finditer(r"(?im)^\s*Диагноз:\s*(.+)$", body or ""):
        name = m.group(1).strip()
        if name:
            hits.append(
                DiagnosisHit(
                    name=name,
                    source=rel,
                    date=date_s,
                    origin_path=rel,
                    origin_kind="history",
                    clinical_trust_tier=str(meta.get("trust_tier") or ""),
                    verification_status="unverified",
                    notes="Из тела markdown (Диагноз:)",
                )
            )

    return hits


def _history_roots(data_dir: Path) -> list[Path]:
    roots = []
    for name in ("Анализы", "УЗИ", "МРТ-КТ", "Терапевт", "schedule"):
        p = data_dir / name
        if p.is_dir():
            roots.append(p)
    return roots


def _collect_from_history(data_dir: Path) -> list[DiagnosisHit]:
    hits: list[DiagnosisHit] = []
    for root in _history_roots(data_dir):
        for path in sorted(root.rglob("*.md")):
            hits.extend(_scan_history_file(path, data_dir))
    return hits


def _collect_from_strategy(data_dir: Path) -> list[DiagnosisHit]:
    path = data_dir / "стратегия.md"
    if not path.exists():
        return []
    meta, body = _read_md(path)
    hits: list[DiagnosisHit] = []
    # Pull diagnosis-like lines from strategy body
    for m in re.finditer(
        r"(?im)(?:диагноз|по поводу|контроль)\s*[:—-]?\s*(.{8,80})",
        body or "",
    ):
        name = m.group(1).strip().rstrip(".")
        if len(name) < 8:
            continue
        hits.append(
            DiagnosisHit(
                name=name,
                source="стратегия.md",
                date=str(meta.get("date") or ""),
                origin_path="стратегия.md",
                origin_kind="strategy",
                verification_status="unverified",
                notes="Упоминание в стратегии (контекст, не самостоятельный диагноз)",
            )
        )
    return hits


def _dedupe(hits: list[DiagnosisHit]) -> list[DiagnosisHit]:
    """Prefer profile rows; keep unique names (normalized)."""
    by_key: dict[str, DiagnosisHit] = {}
    order_rank = {"profile": 0, "history": 1, "schedule": 2, "strategy": 3}
    for h in hits:
        k = h.key()
        if k not in by_key:
            by_key[k] = h
            continue
        cur = by_key[k]
        # Prefer profile; merge sources
        if order_rank.get(h.origin_kind, 9) < order_rank.get(cur.origin_kind, 9):
            h.notes = (h.notes + f"; also {cur.origin_path}").strip("; ")
            by_key[k] = h
        else:
            if h.origin_path and h.origin_path not in (cur.source + cur.notes):
                cur.notes = (cur.notes + f"; also {h.origin_path}").strip("; ")
    return list(by_key.values())


def _match_rule(name: str) -> tuple[str, int, str]:
    low = name.lower()
    for needle, specialist, urgency, dms in RULES:
        if needle in low:
            return specialist, urgency, dms
    return "Терапевт (маршрутизация)", 2, "Консультация терапевта покрывается — получить направления к спецам"


def _load_insurance_summary(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "страховка.md"
    if not path.exists():
        return {"path": str(path), "found": False}
    meta, body = _read_md(path)
    policies = meta.get("policies") or []
    p0 = policies[0] if policies else {}
    return {
        "found": True,
        "path": "страховка.md",
        "insurer": p0.get("insurer") or "Белгосстрах",
        "program": p0.get("program") or "АВгос+ком",
        "sum_insured": p0.get("sum_insured"),
        "remaining": p0.get("remaining"),
        "expiry": p0.get("expiry"),
        "policy": p0.get("policy"),
        "source": meta.get("source"),
        "body_excerpt": (body or "")[:1200],
    }


def write_audit_md(path: Path, hits: list[DiagnosisHit], insurance: dict) -> None:
    today = date.today().isoformat()
    lines = [
        "---",
        "trust_tier: unverified",
        f"date: '{today}'",
        "tags:",
        "  - audit",
        "  - diagnoses",
        "  - dms",
        "  - verification",
        "source: scripts/audit_diagnoses.py",
        f"count: {len(hits)}",
        "verification_status: unverified  # all items need insurance/clinic re-confirm",
        "---",
        "",
        "# Аудит диагнозов — legacy → unverified",
        "",
        f"**Дата аудита:** {today}  ",
        f"**Полис (справка):** {insurance.get('insurer')} · {insurance.get('program')} · "
        f"остаток {insurance.get('remaining')} BYN · до {insurance.get('expiry')}",
        "",
        "Все перечисленные диагнозы помечены **`verification_status: unverified`** — "
        "для официальной фиксации в ОМС/ДМС и маршрута «Этап 1 Конвейера» (терапевт → направления).",
        "",
        "> Клинический `trust_tier` из источника (лаборатория/УЗИ) ≠ подтверждение для страховки. "
        "Страховке нужна актуальная запись у врача по полису.",
        "",
        "## Сводка",
        "",
        f"- Всего уникальных позиций: **{len(hits)}**",
        f"- Профиль (карточка.md): **{sum(1 for h in hits if h.origin_kind == 'profile')}**",
        f"- История/визиты: **{sum(1 for h in hits if h.origin_kind == 'history')}**",
        f"- Прочее: **{sum(1 for h in hits if h.origin_kind not in ('profile', 'history'))}**",
        "",
        "## Диагнозы",
        "",
    ]
    # profile first, then by status emoji priority
    def sort_key(h: DiagnosisHit):
        rank = 0 if "🔴" in h.status else 1 if "🟡" in h.status else 2
        return (0 if h.origin_kind == "profile" else 1, rank, h.name.lower())

    for i, h in enumerate(sorted(hits, key=sort_key), 1):
        lines += [
            f"### {i}. {h.name}",
            "",
            f"| Поле | Значение |",
            f"|------|----------|",
            f"| **verification_status** | `unverified` |",
            f"| Клинический trust_tier | {h.clinical_trust_tier or '—'} |",
            f"| Статус в карточке | {h.status or '—'} |",
            f"| Дата | {h.date or '—'} |",
            f"| Источник | {h.source or '—'} |",
            f"| Файл | `{h.origin_path}` ({h.origin_kind}) |",
            f"| Примечание | {h.notes or '—'} |",
            "",
        ]

    lines += [
        "## YAML (machine-readable)",
        "",
        "```yaml",
        "diagnoses_audit:",
    ]
    for h in sorted(hits, key=lambda x: x.name.lower()):
        lines.append(f"  - name: {yaml.dump(h.name, allow_unicode=True).strip()}")
        lines.append(f"    verification_status: unverified")
        lines.append(f"    clinical_trust_tier: {h.clinical_trust_tier or 'null'}")
        lines.append(f"    status: {yaml.dump(h.status or '', allow_unicode=True).strip()}")
        lines.append(f"    date: {h.date or 'null'}")
        lines.append(f"    origin: {h.origin_path}")
        lines.append(f"    source: {yaml.dump(h.source or '', allow_unicode=True).strip()}")
    lines += ["```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_verification_plan(
    path: Path,
    hits: list[DiagnosisHit],
    insurance: dict,
) -> None:
    today = date.today().isoformat()
    # Build plan rows from profile-primary list preferred
    profile_first = sorted(
        hits,
        key=lambda h: (
            0 if h.origin_kind == "profile" else 1,
            0 if "🔴" in h.status else 1 if "🟡" in h.status else 2,
            h.name.lower(),
        ),
    )

    # Group by specialist
    by_spec: dict[str, list[tuple[DiagnosisHit, int, str]]] = {}
    rows: list[tuple[DiagnosisHit, str, int, str]] = []
    for h in profile_first:
        # Skip pure lab parameter noise if we already have profile name covering it?
        specialist, urgency, dms = _match_rule(h.name)
        rows.append((h, specialist, urgency, dms))
        by_spec.setdefault(specialist, []).append((h, urgency, dms))

    lines = [
        "---",
        "trust_tier: unverified",
        f"date: '{today}'",
        "tags:",
        "  - verification-plan",
        "  - dms",
        "  - pipeline-stage-1",
        "  - therapist",
        "source: scripts/audit_diagnoses.py + data/страховка.md",
        "status: draft",
        "---",
        "",
        "# План верификации диагнозов (ДМС) — черновик для врача",
        "",
        f"**Дата:** {today}  ",
        f"**Полис:** {insurance.get('source') or insurance.get('policy')}  ",
        f"**Программа:** {insurance.get('insurer')} · {insurance.get('program')}  ",
        f"**Лимит / остаток:** {insurance.get('sum_insured')} / {insurance.get('remaining')} BYN  ",
        f"**Срок:** до {insurance.get('expiry')}",
        "",
        "## Цель",
        "",
        "Выжать максимум из ДМС: официально зафиксировать (или снять) **unverified** "
        "legacy-диагнозы через маршрут **Этап 1 Конвейера — Терапевт → направления к спецам**, "
        "с опорой на покрытие полиса «АВгос+ком».",
        "",
        "## Покрытие полиса (кратко)",
        "",
        "| Покрывается | Не покрывается / лимиты |",
        "|-------------|-------------------------|",
        "| Консультации почти всех спецов | Диетолог, сомнолог, трихолог, косметолог, психиатр, нарколог, мануальный, стом-ортопед/ортодонт |",
        "| УЗИ — без лимита | Лекарства, БАДы |",
        "| КТ ×1, МРТ ×1 за период | Онкология, ВИЧ, гепатиты B/C, туберкулёз, СД 1 типа, психиатрия |",
        "| ФГДС/ФКС ×2 суммарно | Капельницы, остеопатия |",
        "| Лаборатории Хеликс / Инвитро / Синлаб / гос. | Плановая стоматология |",
        "| Массаж ×10, физио, малые операции (гос.) | Высоковостребованные >70 BYN — франшиза 40% |",
        "| Уролог ≤5, гинеколог ≤5 | |",
        "",
        "## Маршрут (Этап 1 → 2 → 3)",
        "",
        "1. **Терапевт (ВОП)** — единый вход: жалобы + legacy-список → направления.  ",
        "2. **Спецы (1 день по возможности)** — кардио, гастро, эндо, уролог, невролог, офтальмолог, проктолог.  ",
        "3. **Анализы / УЗИ / ФГДС** — по направлениям, с учётом лимитов КТ/МРТ/ФГДС.  ",
        "4. **Фиксация в медкарте** — формулировки диагнозов, коды, «для страховки».  ",
        "5. **Этап 4** — финальный разбор; **этап 5** — сливки (массаж/физио) только после.",
        "",
        "### Что сказать терапевту (скрипт)",
        "",
        "> «Нужен чекап и **официальная верификация** старых диагнозов по ДМС: "
        "АГ, гепатоз, контроль билирубина (Жильбер?), ЯБ ДПК в ремиссии, камень почки, "
        "зоб, миопия/ПДС, геморрой, трохантерит; плюс невростатус по старой МРТ. "
        "Прошу направления к спецам и на базовые анализы/УЗИ. Жалобы: пульс 80–85, "
        "контроль АД, тяжесть в правом подреберье, …»",
        "",
        "## Таблица: диагноз → врач → срочность → страховка",
        "",
        "| # | Диагноз | Врач | Срочность | Покрытие ДМС | verification |",
        "|---|---------|------|-----------|--------------|--------------|",
    ]

    for i, (h, specialist, urgency, dms) in enumerate(rows, 1):
        if h.origin_kind == "strategy":
            continue  # noise
        # Prefer listing profile + high-signal history
        if h.origin_kind == "history" and "—" in h.name and len(h.name) > 60:
            continue
        urg = URGENCY_LABEL.get(urgency, str(urgency))
        name_short = h.name.replace("|", "/")[:80]
        dms_short = dms.replace("|", "/")[:90]
        lines.append(
            f"| {i} | {name_short} | {specialist} | {urg} | {dms_short} | `unverified` |"
        )

    lines += [
        "",
        "## Пакеты направлений (для 1 визита к терапевту)",
        "",
        "### Пакет A — Кардио (срочность высокая)",
        "",
        "- Кардиолог  ",
        "- ЭКГ, при согласовании Эхо-КГ / Холтер  ",
        "- Биохимия + липиды, глюкоза  ",
        "- **Зачем:** АГ 2 ст., риск 2; пульс 80–85  ",
        "- **ДМС:** консультация + лаборатория; высокочек — франшиза 40%",
        "",
        "### Пакет B — Гастро",
        "",
        "- Гастроэнтеролог  ",
        "- УЗИ органов брюшной полости (повтор, без лимита)  ",
        "- АлАТ, АСТ, билирубин (прямой/непрямой), ЩФ  ",
        "- ФГДС — только если клиника/показания (лимит 2 с ФКС)  ",
        "- **Зачем:** гепатоз, Жильбер?, ЯБ ДПК ремиссия, деформация ЖП",
        "",
        "### Пакет C — Урология",
        "",
        "- Уролог (лимит 5)  ",
        "- УЗИ почек  ",
        "- **Зачем:** МКБ 3.5 мм (2024) — актуален ли камень?",
        "",
        "### Пакет D — Эндокринология",
        "",
        "- Эндокринолог  ",
        "- УЗИ ЩЖ  ",
        "- ТТГ, св.Т4 (± Т3)  ",
        "- **Зачем:** узловой нетоксический зоб 6 мм",
        "",
        "### Пакет E — Прочее (планово)",
        "",
        "- Офтальмолог — миопия / ПДС  ",
        "- Проктолог — геморрой 2 ст.  ",
        "- Ортопед/невролог — трохантерит / старые экструзии (МРТ повтор **не** тратить без симптомов; лимит МРТ ×1)",
        "",
        "## Группировка по специалистам",
        "",
    ]

    for spec, items in sorted(by_spec.items(), key=lambda x: min(u for _, u, _ in x[1])):
        lines.append(f"### {spec}")
        lines.append("")
        for h, urgency, _ in sorted(items, key=lambda t: t[1]):
            if h.origin_kind == "strategy":
                continue
            lines.append(
                f"- **{h.name}** — {URGENCY_LABEL.get(urgency, urgency)} · `unverified` · _{h.origin_path}_"
            )
        lines.append("")

    lines += [
        "## Приоритет визитов (рекомендуемый порядок)",
        "",
        "1. Терапевт → пакет направлений A+B+C+D  ",
        "2. Кардиолог + гастро (+ УЗИ БП) в один день, если возможно  ",
        "3. Лаборатория натощак  ",
        "4. Эндокринолог / уролог  ",
        "5. Офтальмолог, проктолог, ортопед — по слотам  ",
        "6. Предупредить Белгосстрах **до** платных визитов (см. insurance_warned в Конвейере)",
        "",
        "## Контакты страховки",
        "",
        "- Тел. +375 222 71 30 71  ",
        "- Viber +375 29 66 11 965  ",
        "- dms.mogilev@bgs.by",
        "",
        "## Disclaimer",
        "",
        "Черновик для обсуждения с врачом, **не** замена очной консультации. "
        "Решения о диагнозах и назначениях — только врач. Лимиты полиса уточнять у БГС.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def patch_profile_unverified(data_dir: Path) -> int:
    """Add verification_status: unverified to each diagnosis in карточка.md."""
    path = data_dir / "карточка.md"
    if not path.exists():
        return 0
    meta, body = _read_md(path)
    diags = meta.get("diagnoses") or []
    n = 0
    for d in diags:
        if not isinstance(d, dict):
            continue
        d["verification_status"] = "unverified"
        n += 1
    meta["diagnoses"] = diags
    # preserve body
    dumped = yaml.dump(
        meta,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    path.write_text(f"---\n{dumped}---{body}", encoding="utf-8")
    return n


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to tenant data dir (default: <repo>/data/users/80101636)",
    )
    ap.add_argument(
        "--no-patch-profile",
        action="store_true",
        help="Do not write verification_status into карточка.md",
    )
    args = ap.parse_args(argv)
    data_dir = (
        args.data_dir or (_project_root() / "data" / "users" / "80101636")
    ).resolve()
    if not data_dir.is_dir():
        print(f"data dir not found: {data_dir}", file=sys.stderr)
        return 1

    hits = _collect_from_profile(data_dir)
    hits += _collect_from_history(data_dir)
    hits += _collect_from_strategy(data_dir)
    hits = _dedupe(hits)
    # Ensure every hit is unverified
    for h in hits:
        h.verification_status = "unverified"

    insurance = _load_insurance_summary(data_dir)

    audit_path = data_dir / "диагнозы_аудит.md"
    plan_path = data_dir / "verification_plan.md"
    write_audit_md(audit_path, hits, insurance)
    write_verification_plan(plan_path, hits, insurance)

    patched = 0
    if not args.no_patch_profile:
        patched = patch_profile_unverified(data_dir)

    print(f"diagnoses collected: {len(hits)}")
    print(f"wrote: {audit_path}")
    print(f"wrote: {plan_path}")
    if patched:
        print(f"patched карточка.md diagnoses with verification_status=unverified: {patched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
