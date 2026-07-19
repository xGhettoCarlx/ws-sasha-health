"""Build Gemini pre-visit prompt markdown from agent dual-write files.

Used by Timeline «Нужен промпт» → Telegram document delivery.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.storage import MDStorage

PROFILE_PATH = "карточка.md"
COMPLAINTS_PATH = "копилка_жалоб.md"
STRATEGY_PATH = "стратегия.md"
SCHEDULE_DIR = "schedule"


def _store() -> MDStorage:
    return MDStorage()


def _read_meta(store: MDStorage, rel: str) -> tuple[dict, str]:
    try:
        return store.read(rel)
    except FileNotFoundError:
        return {}, ""


def load_visit(store: MDStorage, visit_id: str) -> dict[str, Any]:
    path = f"{SCHEDULE_DIR}/{visit_id}.md"
    meta, body = store.read(path)
    out = {k: v for k, v in meta.items() if not str(k).startswith("_")}
    if body:
        out["content"] = body
    out["id"] = out.get("id") or visit_id
    return out


def _load_complaints(store: MDStorage) -> list[dict]:
    meta, _ = _read_meta(store, COMPLAINTS_PATH)
    entries = meta.get("entries") or []
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict) and not e.get("resolved")]


def _scan_abnormal_labs(store: MDStorage) -> list[dict]:
    cat = store.base_dir / "Анализы"
    if not cat.is_dir():
        return []
    abnormal: list[dict] = []
    normal = {"✅", "✔", "✓", "ok", "normal", "n", "норм", "—", "-"}
    for bundle in sorted(cat.iterdir()):
        if not bundle.is_dir():
            continue
        for md in bundle.glob("*.md"):
            try:
                meta, _ = store.read(str(md.relative_to(store.base_dir)))
            except Exception:
                continue
            for p in meta.get("parameters") or []:
                if not isinstance(p, dict):
                    continue
                flag = str(p.get("flag") or "").strip()
                if not flag or flag.lower() in normal or flag in normal:
                    continue
                if any(
                    ch in flag
                    for ch in ("🔴", "⚠", "↑", "↓", "high", "low", "H", "L")
                ) or flag.lower() in ("high", "low", "h", "l", "abnormal"):
                    abnormal.append(
                        {
                            "date": meta.get("date", ""),
                            "test": meta.get("test_name") or bundle.name,
                            "name": p.get("name"),
                            "value": p.get("value"),
                            "unit": p.get("unit"),
                            "ref_range": p.get("ref_range"),
                            "flag": flag,
                        }
                    )
    return abnormal


def _specialty_key(visit: dict) -> str:
    blob = " ".join(
        str(visit.get(k) or "")
        for k in ("specialty", "doctor", "purpose", "title")
    ).lower()
    mapping = [
        ("кардио", "Кардиолог"),
        ("гастро", "Гастроэнтеролог"),
        ("лор", "ЛОР"),
        ("эндокрин", "Эндокринолог"),
        ("невролог", "Невролог"),
        ("терапевт", "Терапевт"),
        ("воп", "Терапевт"),
        ("массаж", "Сливки"),
        ("физио", "Сливки"),
        ("лаборат", "Анализы"),
        ("анализ", "Анализы"),
    ]
    for needle, label in mapping:
        if needle in blob:
            return label
    if visit.get("specialty"):
        return str(visit["specialty"])
    return "Специалист"


def _visits_same_specialty(store: MDStorage, specialty: str) -> list[dict]:
    key = specialty.lower()
    out: list[dict] = []
    try:
        metas = store.list_dir(SCHEDULE_DIR)
    except Exception:
        metas = []
    for m in metas:
        blob = " ".join(
            str(m.get(k) or "")
            for k in ("specialty", "doctor", "purpose")
        ).lower()
        if key[:4] in blob or any(
            part in blob for part in key.split() if len(part) > 3
        ):
            out.append({k: v for k, v in m.items() if not str(k).startswith("_")})
    out.sort(key=lambda v: str(v.get("visit_date") or v.get("date") or ""), reverse=True)
    return out


def build_visit_prompt_markdown(
    visit: dict[str, Any],
    *,
    store: Optional[MDStorage] = None,
) -> str:
    """Assemble full markdown for Gemini (Лист 1) + context dump."""
    store = store or _store()
    specialty = _specialty_key(visit)
    doctor = visit.get("doctor") or ""
    institution = visit.get("institution") or ""
    vdate = visit.get("visit_date") or visit.get("effective_date") or visit.get("date") or ""
    vtime = visit.get("time") or ""
    purpose = visit.get("purpose") or ""
    notes = visit.get("notes") or ""

    profile, pbody = _read_meta(store, PROFILE_PATH)
    complaints = _load_complaints(store)
    labs = _scan_abnormal_labs(store)
    _, strategy_body = _read_meta(store, STRATEGY_PATH)
    related = _visits_same_specialty(store, specialty)

    name = profile.get("full_name") or "Пациент"
    dob = profile.get("birth_date") or ""
    diagnoses = profile.get("diagnoses") or []
    allergies = profile.get("allergies") or []

    diag_lines = []
    for d in diagnoses:
        if isinstance(d, dict):
            diag_lines.append(
                f"- {d.get('status', '')} **{d.get('name', '')}** "
                f"({d.get('date', '—')}) — {d.get('source') or '—'}"
            )
        else:
            diag_lines.append(f"- {d}")

    c_lines = [
        f"- [{c.get('date')}] sev={c.get('severity')}: {c.get('text')} "
        f"({c.get('specialty_hint') or '—'})"
        for c in complaints[:30]
    ]
    lab_lines = [
        f"- {l.get('date')} · {l.get('test')}: **{l.get('name')}** = "
        f"{l.get('value')} {l.get('unit') or ''} "
        f"(норма {l.get('ref_range') or '—'}, flag {l.get('flag')})"
        for l in labs[:40]
    ]
    hist_lines = []
    for h in related[:15]:
        hist_lines.append(
            f"- {h.get('visit_date') or h.get('date') or '—'} · "
            f"{h.get('status')} · {h.get('doctor')}: {h.get('purpose') or ''}"
            f"{(' — ' + h.get('notes')) if h.get('notes') else ''}"
        )

    anthropo = (pbody or "").strip().splitlines()
    anthropo_s = anthropo[0] if anthropo else ""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Operator-facing package: context + ready Gemini instruction
    gemini_instruction = f"""Ты — медицинский редактор. Сгенерируй ОДИН лист «Лист 1 — ВРАЧУ» на русском
для распечатки перед приёмом. Мягкий язык, без императивов и без диагнозов от ИИ.
Формат: markdown, одна страница, чекбоксы ☐ только для исследований вне нормы.

КОНТЕКСТ ПАЦИЕНТА
ФИО: {name}
ДР: {dob}
Антропометрия: {anthropo_s}
Специалист: {specialty}
Врач: {doctor or "—"}
Учреждение: {institution or "—"}
Дата/время визита: {vdate} {vtime}
Цель визита: {purpose}

ДИАГНОЗЫ (из карты пациента, не интерпретировать заново):
{chr(10).join(diag_lines) or "- (нет в карте)"}

АЛЛЕРГИИ: {", ".join(allergies) if allergies else "не указаны"}

НАКОПЛЕННЫЕ ЖАЛОБЫ (самоотчёт пациента):
{chr(10).join(c_lines) or "- (копилка пуста)"}

РЕЗУЛЬТАТЫ ВНЕ НОРМЫ (из файлов анализов):
{chr(10).join(lab_lines) or "- (нет помеченных отклонений в файлах)"}

ИСТОРИЯ ВИЗИТОВ ПО ЭТОМУ ПРОФИЛЮ:
{chr(10).join(hist_lines) or "- (нет в schedule/)"}

ЗАМЕТКИ К ВИЗИТУ:
{notes or "—"}

ФРАГМЕНТ СТРАТЕГИИ:
{(strategy_body or "")[:1600]}

ТРЕБОВАНИЯ К ВЫВОДУ
1) Заголовок: # Лист 1 — ВРАЧУ
2) Блок ПРОФИЛЬ (ФИО, ДР, специалист)
3) Диагнозы списком
4) ─── ЖАЛОБЫ ─── с эмодзи-категориями по системам
5) ─── 🔴 РЕЗУЛЬТАТЫ ВНЕ НОРМЫ ─── только отклонения + «буду рад направлениям, если сочтёте нужным»
6) Никаких «НУЖНО/ОБЯЗАТЕЛЬНО/КРИТИЧЕСКИ»
7) В конце: дисклеймер «не заменяет очный осмотр»

Верни только готовый markdown листа, без преамбулы.
"""

    header = f"""# Pre-Visit промпт · {specialty}

generated_at: {now}
visit_id: {visit.get("id") or "—"}
doctor: {doctor or "—"}
institution: {institution or "—"}
when: {vdate} {vtime}
pipeline_stage: {visit.get("pipeline_stage") or "—"}

> Файл собран мини-аппом sasha-health (Timeline → «Нужен промпт»).
> Скопируй блок GEMINI ниже в Gemini → получи «Лист 1 — ВРАЧУ».

---

## Визит

- **Цель:** {purpose or "—"}
- **Заметки:** {notes or "—"}

## Жалобы (открытые)

{chr(10).join(c_lines) or "_пусто_"}

## Диагнозы

{chr(10).join(diag_lines) or "_нет_"}

## Анализы вне нормы

{chr(10).join(lab_lines) or "_нет_"}

## История по специалисту

{chr(10).join(hist_lines) or "_нет_"}

---

## GEMINI

```text
{gemini_instruction.strip()}
```
"""
    return header.strip() + "\n"


def write_prompt_file(
    markdown: str,
    *,
    visit_id: str,
    store: Optional[MDStorage] = None,
) -> Path:
    """Persist prompt under data/export/prompts/ and return path."""
    store = store or _store()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^\w\-]+", "_", visit_id)[:48] or "visit"
    rel_dir = Path("export") / "prompts"
    abs_dir = store.base_dir / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    name = f"previsit_{safe}_{stamp}.md"
    path = abs_dir / name
    path.write_text(markdown, encoding="utf-8")
    return path


def resolve_operator_chat_id(user: dict | None = None) -> Optional[int]:
    """Prefer TELEGRAM_CHAT_ID, then authenticated Telegram user id."""
    from app.config import get_settings

    settings = get_settings()
    if settings.TELEGRAM_CHAT_ID:
        return int(settings.TELEGRAM_CHAT_ID)
    if user and user.get("id"):
        try:
            uid = int(user["id"])
            if uid > 0:
                return uid
        except (TypeError, ValueError):
            pass
    # Operator hard default from Station (admin)
    return 80101636
