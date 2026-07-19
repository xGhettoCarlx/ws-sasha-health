"""Medical 5-stage pipeline, timeline, and Trojan Horse API.

GET  /api/pipeline              — stages 1–5 with visits + progress
GET  /api/timeline              — past (by year/month) + future visits
PATCH /api/schedule/{id}/insurance-warned  — toggle insurance flag (also here)
GET  /api/trojan                — Trojan Horse packs
PUT  /api/trojan                — save selected specialty + complaint mix
POST /api/trojan/compose        — preview composed script for checkup approval
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_auth
from app.storage import MDStorage

router = APIRouter(tags=["pipeline"])

# re-export schedule dir name used by prompt trigger
_PROMPT_SCHEDULE = "schedule"

SCHEDULE_DIR = "schedule"
TROJAN_PATH = "trojan_horse.md"
COMPLAINTS_PATH = "копилка_жалоб.md"
HISTORY_ROOTS = ("Анализы", "УЗИ", "МРТ-КТ", "Терапевт")

PIPELINE_STAGES: list[dict[str, Any]] = [
    {
        "stage": 1,
        "key": "therapist",
        "title": "Терапевт",
        "goal": "Получение направлений",
        "icon": "stethoscope",
        "color": "#007AFF",
    },
    {
        "stage": 2,
        "key": "specialists",
        "title": "Спецы",
        "goal": "Собрать в 1 день · назначения на анализы",
        "icon": "users",
        "color": "#AF52DE",
    },
    {
        "stage": 3,
        "key": "labs",
        "title": "Анализы и тесты",
        "goal": "Сдать всё по направлениям",
        "icon": "flask",
        "color": "#FF9500",
    },
    {
        "stage": 4,
        "key": "final",
        "title": "Финальный приём",
        "goal": "Разбор результатов с врачом",
        "icon": "file-check",
        "color": "#34C759",
    },
    {
        "stage": 5,
        "key": "cream",
        "title": "Сливки",
        "goal": "Процедуры, массажи, реабилитация",
        "icon": "sparkles",
        "color": "#FF2D55",
    },
]

# Default «усиления» for guaranteed checkup approval by specialty
DEFAULT_BOOSTERS: dict[str, list[dict[str, str]]] = {
    "Кардиология": [
        {
            "id": "boost-cardio-1",
            "text": "Периодические перебои / ощущение «замирания» сердца в покое",
            "rationale": "Обосновывает Эхо-КГ + Холтер",
        },
        {
            "id": "boost-cardio-2",
            "text": "Одышка при умеренной нагрузке, которую раньше не замечал",
            "rationale": "Усиливает чекап-набор кардио",
        },
        {
            "id": "boost-cardio-3",
            "text": "Семейный анамнез АГ / аритмий (уточнить на приёме)",
            "rationale": "Фактор риска для расширенного обследования",
        },
    ],
    "Гастроэнтерология": [
        {
            "id": "boost-gastro-1",
            "text": "Тяжесть / дискомфорт в правом подреберье после жирной пищи",
            "rationale": "УЗИ БП + биохимия печени",
        },
        {
            "id": "boost-gastro-2",
            "text": "Эпизоды тошноты, снижение переносимости еды",
            "rationale": "Подкрепляет ФГДС при необходимости",
        },
    ],
    "ЛОР": [
        {
            "id": "boost-lor-1",
            "text": "Хроническая заложенность носа, ночная гипоксия / храп",
            "rationale": "Риноскопия + связь с АГ/пульсом",
        },
        {
            "id": "boost-lor-2",
            "text": "Частые простуды / стекание по задней стенке",
            "rationale": "Осмотр ЛОР, возможный синусит",
        },
    ],
    "Эндокринология": [
        {
            "id": "boost-endo-1",
            "text": "Колебания веса, утомляемость, холодные конечности",
            "rationale": "ТТГ / Т3 / Т4 + УЗИ щитовидной",
        },
    ],
    "Терапия": [
        {
            "id": "boost-ther-1",
            "text": "Нужен полный чекап: направления на базовые анализы и спецов",
            "rationale": "Этап 1 конвейера — пакет направлений",
        },
    ],
}


def _store() -> MDStorage:
    return MDStorage()


def _parse_date(raw: Any) -> Optional[date]:
    if raw is None or raw == "":
        return None
    s = str(raw).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _effective_date(visit: dict) -> Optional[date]:
    """Prefer visit_date, then date field."""
    return _parse_date(visit.get("visit_date")) or _parse_date(visit.get("date"))


def resolve_visit_status(visit: dict) -> str:
    """Normalize visit status for pipeline/timeline.

    Rules (HEALTH-PIPELINE-STATUS-SEPARATION):
      - completed / cancelled stay as-is
      - has real date (visit_date or date) → booked
      - no date → draft (agent recommendation / need to book)
      - legacy planned/pending mapped via date presence
    """
    raw = str(visit.get("status") or "").strip().lower()
    if raw in ("completed", "cancelled"):
        return raw
    if _effective_date(visit) is not None:
        return "booked"
    return "draft"


def apply_status_on_save(meta: dict) -> dict:
    """When creating/updating a visit: date present → booked, else draft.

    Terminal statuses (completed/cancelled) are preserved.
    """
    raw = str(meta.get("status") or "").strip().lower()
    if raw in ("completed", "cancelled"):
        meta["status"] = raw
        return meta
    meta["status"] = resolve_visit_status(meta)
    return meta


OPEN_STATUSES = frozenset({"draft", "booked", "planned", "pending"})


def _infer_stage(visit: dict) -> int:
    """Map visit to pipeline stage 1–5 from explicit field or heuristics."""
    raw = visit.get("pipeline_stage")
    if raw is not None:
        try:
            n = int(raw)
            if 1 <= n <= 5:
                return n
        except (TypeError, ValueError):
            pass

    blob = " ".join(
        str(visit.get(k) or "")
        for k in ("doctor", "purpose", "notes", "specialty", "tags")
    ).lower()
    tags = visit.get("tags") or []
    if isinstance(tags, list):
        blob += " " + " ".join(str(t).lower() for t in tags)

    if any(k in blob for k in ("массаж", "физио", "лфк", "процедур", "сливк", "рекавер", "spa")):
        return 5
    if any(k in blob for k in ("анализ", "оак", "биохим", "узи", "мрт", "экг", "холтер", "лаборат", "флюор")):
        # completed labs vs planned specialist with lab orders
        if visit.get("status") == "completed" and any(
            k in blob for k in ("сдан", "результат", "кровь сдана")
        ):
            return 3
        if any(k in blob for k in ("назнач", "направлен", "сдать")):
            return 3
    if any(k in blob for k in ("финальн", "разбор результат", "повторн", "с результат")):
        return 4
    if any(
        k in blob
        for k in (
            "кардиолог",
            "гастро",
            "лор",
            "эндокрин",
            "невролог",
            "офтальм",
            "хирург",
            "спец",
        )
    ):
        return 2
    if any(k in blob for k in ("терапевт", "воп", "участков", "поликлиник")):
        return 1
    # default future pending → specialists bucket if doctor has specialty paren
    if re.search(r"\([^)]+\)", str(visit.get("doctor") or "")):
        return 2
    return 1


def _normalize_visit(meta: dict) -> dict:
    v = {k: val for k, val in meta.items() if not str(k).startswith("_")}
    v["pipeline_stage"] = _infer_stage(v)
    if "insurance_warned" not in v:
        v["insurance_warned"] = False
    else:
        v["insurance_warned"] = bool(v.get("insurance_warned"))
    eff = _effective_date(v)
    v["effective_date"] = eff.isoformat() if eff else None
    # draft | booked | completed | cancelled (legacy planned/pending collapsed)
    v["status"] = resolve_visit_status(v)
    v["booking_status"] = (
        "draft"
        if v["status"] == "draft"
        else "booked"
        if v["status"] in ("booked", "completed")
        else v["status"]
    )
    return v


def _list_schedule_visits(store: MDStorage) -> list[dict]:
    metas = store.list_dir(SCHEDULE_DIR)
    return [_normalize_visit(m) for m in metas]


def _history_events(store: MDStorage) -> list[dict]:
    """Past clinical events from folder structure (labs, imaging, therapist notes)."""
    events: list[dict] = []
    for root in HISTORY_ROOTS:
        try:
            metas = store.list_dir(root)
        except Exception:
            continue
        for m in metas:
            d = _parse_date(m.get("date"))
            title = m.get("title") or m.get("test_name") or m.get("name") or root
            path = m.get("_path") or m.get("_bundle") or ""
            # Prefer folder name
            if path:
                parts = str(path).replace("\\", "/").split("/")
                if len(parts) >= 2:
                    title = parts[-2] if parts[-1].endswith(".md") else parts[-1]
            events.append(
                {
                    "id": m.get("id") or f"hist-{root}-{m.get('date')}-{title}",
                    "kind": "history",
                    "category": root,
                    "title": str(title),
                    "date": d.isoformat() if d else m.get("date"),
                    "effective_date": d.isoformat() if d else None,
                    "status": "completed",
                    "pipeline_stage": 3 if root in ("Анализы", "УЗИ", "МРТ-КТ") else 1,
                    "doctor": m.get("doctor"),
                    "purpose": m.get("purpose") or m.get("summary"),
                    "insurance_warned": False,
                    "source": "history",
                }
            )
    return events


@router.get("/api/pipeline")
async def get_pipeline(_user: dict = require_auth):
    """Return the 5-stage medical conveyor with visits attached to each stage."""
    store = _store()
    visits = _list_schedule_visits(store)
    by_stage: dict[int, list[dict]] = {i: [] for i in range(1, 6)}
    for v in visits:
        by_stage[int(v["pipeline_stage"])].append(v)

    stages_out = []
    active_stage = 1
    for spec in PIPELINE_STAGES:
        stage_n = spec["stage"]
        items = by_stage[stage_n]
        completed = sum(1 for x in items if x.get("status") == "completed")
        open_n = sum(1 for x in items if x.get("status") in OPEN_STATUSES)
        draft_n = sum(1 for x in items if x.get("status") == "draft")
        booked_n = sum(1 for x in items if x.get("status") == "booked")
        if open_n > 0 and stage_n >= active_stage:
            active_stage = stage_n
        elif completed > 0 and open_n == 0 and stage_n >= active_stage:
            active_stage = min(5, stage_n + 1)
        # Sort: booked first (real appointments), then draft (to-book), then rest
        items_sorted = sorted(
            items,
            key=lambda x: (
                0 if x.get("status") == "booked" else 1 if x.get("status") == "draft" else 2,
                x.get("effective_date") or x.get("date") or "9999",
            ),
        )
        stages_out.append(
            {
                **spec,
                "visits": items_sorted,
                "counts": {
                    "total": len(items),
                    "completed": completed,
                    "open": open_n,
                    "draft": draft_n,
                    "booked": booked_n,
                },
                "status": (
                    "done"
                    if items and completed == len(items)
                    else "active"
                    if open_n
                    else "empty"
                ),
            }
        )

    # If all empty, stage 1 is active by design
    if all(s["counts"]["total"] == 0 for s in stages_out):
        active_stage = 1
        stages_out[0]["status"] = "active"

    return {
        "stages": stages_out,
        "active_stage": active_stage,
        "total_visits": len(visits),
        "summary": {
            "open": sum(1 for v in visits if v.get("status") in OPEN_STATUSES),
            "draft": sum(1 for v in visits if v.get("status") == "draft"),
            "booked": sum(1 for v in visits if v.get("status") == "booked"),
            "completed": sum(1 for v in visits if v.get("status") == "completed"),
            "insurance_warned": sum(1 for v in visits if v.get("insurance_warned")),
            "insurance_pending": sum(
                1
                for v in visits
                if v.get("status") in OPEN_STATUSES and not v.get("insurance_warned")
            ),
        },
    }


@router.get("/api/timeline")
async def get_timeline(_user: dict = require_auth):
    """Unified timeline: past grouped by year→month, future as flat schedule."""
    store = _store()
    today = date.today()
    visits = _list_schedule_visits(store)
    history = _history_events(store)

    past_items: list[dict] = []
    future_items: list[dict] = []

    for v in visits:
        eff = _effective_date(v)
        item = {
            **v,
            "kind": "visit",
            "title": v.get("doctor") or v.get("purpose") or "Визит",
            "source": "schedule",
        }
        if v.get("status") == "completed" or (eff and eff < today):
            if v.get("status") != "cancelled":
                past_items.append(item)
        elif v.get("status") != "cancelled":
            future_items.append(item)

    for h in history:
        eff = _parse_date(h.get("effective_date") or h.get("date"))
        if eff and eff <= today:
            past_items.append(h)
        elif not eff:
            past_items.append(h)

    # Dedupe history by date+title soft key
    seen = set()
    past_deduped = []
    for p in past_items:
        key = (p.get("effective_date") or p.get("date"), p.get("title"), p.get("kind"))
        if key in seen:
            continue
        seen.add(key)
        past_deduped.append(p)

    past_deduped.sort(
        key=lambda x: x.get("effective_date") or x.get("date") or "",
        reverse=True,
    )
    future_items.sort(key=lambda x: x.get("effective_date") or x.get("date") or "9999")

    # Group past by year → month
    by_year: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    undated: list[dict] = []
    month_names = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь",
    }
    for p in past_deduped:
        d = _parse_date(p.get("effective_date") or p.get("date"))
        if not d:
            undated.append(p)
            continue
        by_year[str(d.year)][f"{d.month:02d}"].append(p)

    past_groups = []
    for year in sorted(by_year.keys(), reverse=True):
        months = []
        for month_key in sorted(by_year[year].keys(), reverse=True):
            mnum = int(month_key)
            months.append(
                {
                    "month": month_key,
                    "label": month_names.get(mnum, month_key),
                    "items": by_year[year][month_key],
                }
            )
        past_groups.append({"year": year, "months": months})

    return {
        "today": today.isoformat(),
        "future": future_items,
        "past": {
            "groups": past_groups,
            "undated": undated,
            "count": len(past_deduped),
        },
        "counts": {
            "future": len(future_items),
            "past": len(past_deduped),
            "insurance_unwarned_future": sum(
                1 for f in future_items if not f.get("insurance_warned")
            ),
        },
    }


class InsuranceWarnedBody(BaseModel):
    insurance_warned: bool = True
    bgs_application_number: Optional[str] = None


@router.patch("/api/schedule/{visit_id}/insurance-warned")
async def patch_insurance_warned(
    visit_id: str,
    body: InsuranceWarnedBody,
    user: dict = require_auth,
):
    """Mark insurance (БГС) as warned; store / auto-assign BGS application number."""
    from app.bot import bot_token_usable, send_reminder
    from app.visit_prompt import generate_bgs_application_number, resolve_operator_chat_id

    store = _store()
    path = f"{SCHEDULE_DIR}/{visit_id}.md"
    try:
        meta, content = store.read(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Visit not found") from None
    meta["insurance_warned"] = bool(body.insurance_warned)
    if body.insurance_warned:
        num = (body.bgs_application_number or meta.get("bgs_application_number") or "").strip()
        if not num:
            num = generate_bgs_application_number(visit_id)
        meta["bgs_application_number"] = num
        # Notify operator bot (outbound only)
        chat_id = resolve_operator_chat_id(user)
        if bot_token_usable() and chat_id:
            who = meta.get("doctor") or meta.get("specialty") or visit_id
            try:
                await send_reminder(
                    int(chat_id),
                    (
                        f"🛡 <b>Страховая предупреждена</b>\n"
                        f"{who}\n"
                        f"Заявка БГС: <code>{num}</code>"
                    ),
                )
            except Exception:
                pass
    else:
        # keep number for history but allow re-warn
        pass
    store.write(path, meta, content)
    return _normalize_visit(meta)


class TrojanSaveBody(BaseModel):
    specialty: str = Field(..., min_length=1)
    complaint_ids: list[str] = Field(default_factory=list)
    booster_ids: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


def _load_trojan(store: MDStorage) -> dict:
    try:
        meta, body = store.read(TROJAN_PATH)
    except FileNotFoundError:
        return {
            "specialty": "Кардиология",
            "complaint_ids": [],
            "booster_ids": [],
            "notes": "",
            "content": "",
        }
    meta = dict(meta)
    meta["content"] = body
    meta.setdefault("specialty", "Кардиология")
    meta.setdefault("complaint_ids", [])
    meta.setdefault("booster_ids", [])
    return meta


def _load_open_complaints(store: MDStorage) -> list[dict]:
    try:
        meta, _ = store.read(COMPLAINTS_PATH)
    except FileNotFoundError:
        return []
    entries = meta.get("entries") or []
    out = []
    for e in entries:
        if e.get("resolved"):
            continue
        out.append(
            {
                "id": e.get("id"),
                "text": e.get("text"),
                "severity": e.get("severity"),
                "specialty_hint": e.get("specialty_hint"),
                "date": e.get("date"),
                "tags": e.get("tags") or [],
            }
        )
    return out


@router.get("/api/trojan")
async def get_trojan(_user: dict = require_auth):
    """Trojan Horse: specialty + real complaints + boosters for checkup approval."""
    store = _store()
    saved = _load_trojan(store)
    complaints = _load_open_complaints(store)
    specialties = sorted(
        set(list(DEFAULT_BOOSTERS.keys()) + [saved.get("specialty") or "Кардиология"])
    )
    specialty = saved.get("specialty") or "Кардиология"
    boosters = DEFAULT_BOOSTERS.get(specialty) or DEFAULT_BOOSTERS.get("Терапия") or []
    # also expose all boosters map for UI switching
    return {
        "specialty": specialty,
        "specialties": specialties,
        "boosters": boosters,
        "boosters_by_specialty": DEFAULT_BOOSTERS,
        "complaints": complaints,
        "selected_complaint_ids": list(saved.get("complaint_ids") or []),
        "selected_booster_ids": list(saved.get("booster_ids") or []),
        "notes": saved.get("notes") or "",
        "updated": saved.get("date") or saved.get("updated"),
    }


@router.put("/api/trojan")
async def put_trojan(body: TrojanSaveBody, _user: dict = require_auth):
    """Persist Trojan Horse selection."""
    store = _store()
    meta = {
        "trust_tier": "trusted",
        "date": date.today().isoformat(),
        "tags": ["trojan", "pipeline", body.specialty],
        "specialty": body.specialty,
        "complaint_ids": body.complaint_ids,
        "booster_ids": body.booster_ids,
        "notes": body.notes or "",
        "source": "mini-app",
    }
    body_md = (
        f"# Троянский конь — {body.specialty}\n\n"
        f"Жалобы: {', '.join(body.complaint_ids) or '—'}\n"
        f"Усиления: {', '.join(body.booster_ids) or '—'}\n"
    )
    if body.notes:
        body_md += f"\n## Заметки\n\n{body.notes}\n"
    store.write(TROJAN_PATH, meta, body_md)
    # rebuild response same as GET
    complaints = _load_open_complaints(store)
    specialty = body.specialty
    boosters = DEFAULT_BOOSTERS.get(specialty) or DEFAULT_BOOSTERS.get("Терапия") or []
    specialties = sorted(set(list(DEFAULT_BOOSTERS.keys()) + [specialty]))
    return {
        "specialty": specialty,
        "specialties": specialties,
        "boosters": boosters,
        "boosters_by_specialty": DEFAULT_BOOSTERS,
        "complaints": complaints,
        "selected_complaint_ids": list(body.complaint_ids),
        "selected_booster_ids": list(body.booster_ids),
        "notes": body.notes or "",
        "updated": meta["date"],
        "ok": True,
    }


class TrojanComposeBody(BaseModel):
    specialty: str
    complaint_ids: list[str] = Field(default_factory=list)
    booster_ids: list[str] = Field(default_factory=list)


class VisitPromptBody(BaseModel):
    """Optional overrides when triggering pre-visit prompt to Telegram."""

    chat_id: Optional[int] = None
    dry_run: bool = False  # force no Telegram even if token set


@router.post("/api/visits/{visit_id}/prompt")
async def trigger_visit_prompt(
    visit_id: str,
    body: VisitPromptBody | None = None,
    user: dict = require_auth,
):
    """Build pre-visit prompt package and signal the Telegram bot.

    «Нужен промпт» / «Страховая» flow:
      open visit (draft | booked) → markdown + print HTML → Telegram document.
    Marks visit.prompt_ready for Mini App download button.
    """
    from app.bot import bot_token_usable, send_document
    from app.visit_prompt import (
        build_visit_prompt_markdown,
        load_visit,
        resolve_operator_chat_id,
        write_print_html,
        write_prompt_file,
    )

    body = body or VisitPromptBody()
    store = _store()
    try:
        visit = load_visit(store, visit_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"visit not found: {visit_id}") from None

    status = resolve_visit_status(visit)
    if status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail="prompt only for open visits (draft / booked)",
        )

    md = build_visit_prompt_markdown(visit, store=store)
    path = write_prompt_file(md, visit_id=visit_id, store=store)
    html_path = write_print_html(md, visit_id=visit_id, store=store, md_path=path)
    chat_id = body.chat_id or resolve_operator_chat_id(user)

    # Persist readiness on the visit card for Mini App download button
    vpath = f"{SCHEDULE_DIR}/{visit_id}.md"
    try:
        meta, content = store.read(vpath)
        meta["prompt_ready"] = True
        meta["prompt_path"] = str(path.relative_to(store.base_dir)) if path.is_relative_to(store.base_dir) else str(path)
        meta["prompt_pdf_path"] = (
            str(html_path.relative_to(store.base_dir))
            if html_path.is_relative_to(store.base_dir)
            else str(html_path)
        )
        meta["prompt_generated_at"] = datetime.now().isoformat(timespec="seconds")
        store.write(vpath, meta, content)
    except Exception:
        pass

    telegram_sent = False
    telegram_error: Optional[str] = None
    if body.dry_run:
        telegram_error = "dry_run"
    elif not bot_token_usable():
        telegram_error = "BOT_TOKEN placeholder or missing — file saved only"
    elif not chat_id:
        telegram_error = "no chat_id (set TELEGRAM_CHAT_ID)"
    else:
        try:
            status_label = "нужно записаться" if status == "draft" else "записан"
            caption = (
                f"🧾 <b>Промпт к визиту</b> ({status_label})\n"
                f"{visit.get('doctor') or visit.get('specialty') or visit_id}\n"
                f"{visit.get('visit_date') or visit.get('date') or 'дата не назначена'} "
                f"{visit.get('time') or ''}"
            ).strip()
            telegram_sent = await send_document(
                int(chat_id),
                path,
                caption=caption,
                filename=path.name,
            )
            if not telegram_sent:
                telegram_error = "Telegram send_document returned False"
        except Exception as exc:
            telegram_error = str(exc)[:300]

    return {
        "ok": True,
        "visit_id": visit_id,
        "specialty": visit.get("specialty"),
        "doctor": visit.get("doctor"),
        "path": str(path),
        "pdf_path": str(html_path),
        "pdf_ready": True,
        "download_url": f"/api/visits/{visit_id}/prompt/download",
        "bytes": path.stat().st_size,
        "chat_id": chat_id,
        "telegram_sent": telegram_sent,
        "telegram_error": telegram_error,
        "bot_token_usable": bot_token_usable(),
        "hint": (
            "Промпт отправлен в Telegram · можно скачать PDF для печати"
            if telegram_sent
            else f"Промпт сохранён · скачайте PDF для печати. {telegram_error or ''}"
        ),
    }


@router.get("/api/visits/{visit_id}/prompt/download")
async def download_visit_prompt(
    visit_id: str,
    _user: dict = require_auth,
):
    """Download print-ready prompt package (HTML → Print → PDF)."""
    from starlette.responses import FileResponse

    from app.visit_prompt import latest_prompt_files, load_visit

    store = _store()
    try:
        visit = load_visit(store, visit_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"visit not found: {visit_id}") from None

    files = latest_prompt_files(store, visit_id)
    # Prefer explicit paths on visit meta
    preferred: list[Path] = []
    for key in ("prompt_pdf_path", "prompt_path"):
        rel = visit.get(key)
        if rel:
            p = Path(str(rel))
            if not p.is_absolute():
                p = store.base_dir / p
            if p.is_file():
                preferred.append(p)
    if files.get("html"):
        preferred.append(files["html"])  # type: ignore[arg-type]
    if files.get("md"):
        preferred.append(files["md"])  # type: ignore[arg-type]

    if not preferred:
        raise HTTPException(status_code=404, detail="prompt not ready — press «Нужен промпт» first")

    path = preferred[0]
    media = "text/html; charset=utf-8" if path.suffix.lower() == ".html" else "text/markdown; charset=utf-8"
    # Filename suggests print-to-PDF workflow
    download_name = path.name if path.suffix.lower() == ".html" else path.with_suffix(".html").name
    if path.suffix.lower() == ".html":
        download_name = path.name.replace(".html", "-print.html")
    return FileResponse(
        path,
        media_type=media,
        filename=download_name,
    )


@router.post("/api/trojan/compose")
async def compose_trojan(body: TrojanComposeBody, _user: dict = require_auth):
    """Compose a visit script: real complaints + boosters for therapist/specialist."""
    store = _store()
    complaints = {c["id"]: c for c in _load_open_complaints(store) if c.get("id")}
    boosters = {
        b["id"]: b
        for b in (DEFAULT_BOOSTERS.get(body.specialty) or [])
    }
    # include boosters from all specialties if id matches
    for lst in DEFAULT_BOOSTERS.values():
        for b in lst:
            boosters.setdefault(b["id"], b)

    real = [complaints[i] for i in body.complaint_ids if i in complaints]
    boost = [boosters[i] for i in body.booster_ids if i in boosters]

    lines = [
        f"## Направление: {body.specialty}",
        "",
        "### Реальные жалобы (из копилки)",
    ]
    if real:
        for c in real:
            lines.append(f"- {c.get('text')} (severity {c.get('severity') or '—'})")
    else:
        lines.append("- _(не выбраны)_")
    lines += ["", "### Усиления (для аппрува чекапа)"]
    if boost:
        for b in boost:
            lines.append(f"- {b['text']} — _{b.get('rationale', '')}_")
    else:
        lines.append("- _(не выбраны)_")
    lines += [
        "",
        "### Что просить",
        f"- Направления / обследования по профилю **{body.specialty}**",
        "- Фиксация жалоб в медкарте (не «просто посмотреть»)",
        "- Связка с этапом конвейера: 1→2→3 (анализы)→4 (разбор)",
    ]
    script = "\n".join(lines)
    return {
        "specialty": body.specialty,
        "script": script,
        "real_count": len(real),
        "booster_count": len(boost),
        "mix_ok": len(real) > 0 and len(boost) > 0,
    }
