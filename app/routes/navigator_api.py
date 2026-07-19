"""Real-data bridge for the medical navigator Mini App.

Endpoints (all require auth; dev mode allows unauthenticated mock user):
  GET  /api/vitals                 — BP + weight series from дневник/
  POST /api/vitals                 — log BP and/or weight (no pulse/SpO2/temp)
  GET  /api/checkups               — parse чекапы.md table
  PATCH /api/checkups/{slug}       — mark checkup done / set last date
  GET  /api/complaints             — piggy bank of symptoms for next visit
  POST /api/complaints             — append complaint
  DELETE /api/complaints/{id}      — archive (mark resolved) or hard-delete
  GET  /api/navigator              — specialty routing + insurance coverage
  POST /api/previsit               — Zero-API Gemini prompt assembly
  GET  /api/overview               — dashboard aggregate (real files only)
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import require_auth
from app.config import get_settings
from app.storage import MDStorage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["navigator"])

QUICK_DIR = "дневник"
CHECKUPS_PATH = "чекапы.md"
COMPLAINTS_PATH = "копилка_жалоб.md"
PROFILE_PATH = "карточка.md"
INSURANCE_PATH = "страховка.md"
STRATEGY_PATH = "стратегия.md"
SYMPTOMS_PATH = "дневник_симптомов.md"

# Symptom keywords → specialty (RU medical navigator for BY ambulatory care)
NAV_MAP: list[dict[str, Any]] = [
    {
        "specialty": "Кардиолог",
        "keywords": [
            "давлен", "пульс", "сердц", "экстрасистол", "груд", "тахикард",
            "аритм", "экг", "холтер", "гипертон",
        ],
        "covered": True,
        "note": "Консультация кардиолога покрывается (кроме сомнолога).",
        "prep": ["Свежая ЭКГ в день приёма", "Холтер / старые ЭКГ", "Липиды, электролиты"],
    },
    {
        "specialty": "Гастроэнтеролог",
        "keywords": [
            "живот", "подребер", "печень", "желч", "тошнот", "изжог", "желуд",
            "гепатоз", "билирубин", "стул", "эпигастр",
        ],
        "covered": True,
        "note": "Консультация + УЗИ БП (без лимита). ФГДС/ФКС — лимит 2/период.",
        "prep": ["Биохимия (АлАТ/АсАТ/билирубин)", "УЗИ брюшной полости"],
    },
    {
        "specialty": "ЛОР",
        "keywords": [
            "нос", "ринит", "заложен", "храп", "глотк", "ухо", "синус", "аллерг",
            "пыльц",
        ],
        "covered": True,
        "note": "ЛОР покрывается. Ночная гипоксия → связь с АГ (см. стратегию).",
        "prep": ["Дневник заложенности/храпа", "Аллергоанамнез"],
    },
    {
        "specialty": "Эндокринолог",
        "keywords": ["щитовид", "ттг", "зоб", "тирео", "вес", "узел"],
        "covered": True,
        "note": "Консультация покрывается. УЗИ щитовидной — без ограничений.",
        "prep": ["ТТГ / Т3 / Т4", "УЗИ щитовидной железы"],
    },
    {
        "specialty": "Невролог / ортопед",
        "keywords": [
            "поясниц", "спин", "позвон", "нога", "трохантер", "бедро", "мрт",
            "онемен", "ишиас",
        ],
        "covered": True,
        "note": "Консультация покрывается. МРТ — 1 раз за период страховки.",
        "prep": ["МРТ/КТ при наличии", "Описание боли и триггеров"],
    },
    {
        "specialty": "Терапевт / ВОП",
        "keywords": ["общ", "слаб", "температур", "анализ", "направлен", "чекап"],
        "covered": True,
        "note": "Стартовая точка: направления на анализы, ЭКГ, флюорографию.",
        "prep": ["Список нужных направлений", "Актуальные жалобы"],
    },
    {
        "specialty": "Дерматолог",
        "keywords": ["кож", "шелуш", "сып", "зуд", "век", "псориаз"],
        "covered": True,
        "note": "Дерматолог покрывается (косметолог — нет).",
        "prep": ["Фото очагов", "Длительность симптомов"],
    },
    {
        "specialty": "Стоматолог (экстренный)",
        "keywords": ["зуб", "десна", "острая боль зуб"],
        "covered": "limited",
        "note": "Только экстренная стоматология 1 раз/период. Плановая — нет.",
        "prep": [],
    },
    {
        "specialty": "Психиатр / психотерапевт",
        "keywords": ["тревог", "депресс", "паник", "сон наруш"],
        "covered": False,
        "note": "Психиатрия/наркология не покрываются программой АВгос+ком.",
        "prep": [],
    },
]

NOT_COVERED = [
    "лекарства", "БАД", "витамины", "плановая стоматология", "протезирование",
    "имплантация", "онкология (спец.)", "психиатрия", "наркология",
    "диетолог", "сомнолог", "трихолог", "косметолог", "мануальный терапевт",
]


def _store() -> MDStorage:
    return MDStorage(base_dir=get_settings().DATA_DIR)


def _today() -> str:
    return date.today().isoformat()


def _read_meta(store: MDStorage, path: str) -> tuple[dict, str]:
    try:
        return store.read(path)
    except FileNotFoundError:
        return {}, ""


# ── models ────────────────────────────────────────────────────────────────


class VitalCreate(BaseModel):
    """Log blood pressure and/or weight. No pulse/SpO2/temperature."""

    bp: Optional[str] = Field(
        default=None,
        description="Blood pressure as SYS/DIA, e.g. '128/82'",
    )
    weight_kg: Optional[float] = Field(
        default=None, ge=30, le=300, description="Body weight in kg"
    )
    notes: Optional[str] = None
    when: Optional[str] = Field(
        default=None, description="morning | evening | other"
    )


class ComplaintCreate(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    severity: int = Field(default=5, ge=1, le=10)
    specialty_hint: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class PrevisitRequest(BaseModel):
    specialty: str = Field(min_length=2, max_length=80)
    doctor: Optional[str] = None
    institution: Optional[str] = None
    include_abnormal_labs: bool = True
    include_open_complaints: bool = True


class CheckupPatch(BaseModel):
    last_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    status: Optional[str] = Field(
        default=None, description="ok | plan | due | overdue"
    )


# ── helpers: vitals ───────────────────────────────────────────────────────


def _parse_bp(bp: str) -> tuple[int, int] | None:
    m = re.match(r"^(\d{2,3})/(\d{2,3})$", bp.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _coerce_weight(val: object) -> float | None:
    """Accept weight as number or agent string like '99.5 кг' / '99,5'."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"(\d{2,3}(?:[.,]\d+)?)", str(val).replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _coerce_bp(val: object, content: str = "") -> str | None:
    """Normalize BP from meta or free-text agent diary body."""
    if val:
        s = str(val).strip().replace(" ", "")
        parsed = _parse_bp(s)
        if parsed:
            return f"{parsed[0]}/{parsed[1]}"
        # e.g. "АД 126/78" already partially clean
        m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", str(val))
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    if content:
        m = re.search(
            r"(?:ад|давлен\w*|bp)[^\d]{0,12}(\d{2,3})\s*/\s*(\d{2,3})",
            content,
            flags=re.I,
        )
        if m:
            return f"{m.group(1)}/{m.group(2)}"
        m2 = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", content)
        if m2:
            return f"{m2.group(1)}/{m2.group(2)}"
    return None


def _list_vitals(store: MDStorage, limit: int = 60) -> list[dict]:
    d = store.base_dir / QUICK_DIR
    if not d.is_dir():
        return []
    out: list[dict] = []
    for md in sorted(d.glob("*.md"), reverse=True):
        try:
            meta, content = store.read(str(md.relative_to(store.base_dir)))
        except Exception:
            continue
        bp = _coerce_bp(meta.get("bp"), content or "")
        weight = _coerce_weight(
            meta.get("weight_kg")
            if meta.get("weight_kg") is not None
            else meta.get("weight")
        )
        # free-text weight in body: "вес 99.5"
        if weight is None and content:
            wm = re.search(
                r"(?:вес|weight)[^\d]{0,12}(\d{2,3}(?:[.,]\d+)?)\s*кг?",
                content,
                flags=re.I,
            )
            if wm:
                weight = _coerce_weight(wm.group(1))
        item = {
            "id": md.stem,
            "date": meta.get("date") or md.stem[:10],
            "bp": bp,
            "weight_kg": weight,
            "when": meta.get("when"),
            "notes": meta.get("notes") or (content.strip() or None),
            "trust_tier": meta.get("trust_tier", "unverified"),
            "_path": str(md.relative_to(store.base_dir)),
        }
        # skip pure junk without BP or weight
        if item["bp"] or item["weight_kg"] is not None:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _profile_weight(store: MDStorage) -> float | None:
    meta, body = _read_meta(store, PROFILE_PATH)
    # body often has "183 см / 100 кг"
    m = re.search(r"(\d{2,3}(?:[.,]\d+)?)\s*кг", body or "")
    if m:
        return float(m.group(1).replace(",", "."))
    return None


# ── helpers: checkups ─────────────────────────────────────────────────────


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s\-а-яё]", "", s, flags=re.I)
    s = re.sub(r"[\s_]+", "-", s)
    return s[:64] or "item"


def _interval_days(interval: str) -> int:
    t = interval.lower().replace(" ", "")
    if "6" in t and "мес" in t:
        return 183
    if "3" in t and "год" in t:
        return 1095
    if "год" in t or "1г" in t:
        return 365
    if "мес" in t:
        m = re.search(r"(\d+)", t)
        return int(m.group(1)) * 30 if m else 180
    return 365


def _status_from_last(last: str | None, interval: str) -> str:
    if not last or last.lower() in ("нет данных", "—", "-", "n/a"):
        return "overdue"
    try:
        d = date.fromisoformat(last[:10])
    except ValueError:
        return "plan"
    age = (date.today() - d).days
    iv = _interval_days(interval)
    if age > iv:
        return "overdue"
    if age > iv * 0.8:
        return "plan"
    return "ok"


def _parse_checkups_table(body: str) -> list[dict]:
    rows: list[dict] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*:?-{2,}", line) or "Обследование" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        name, interval, last = cells[0], cells[1], cells[2]
        status_cell = cells[3] if len(cells) > 3 else ""
        computed = _status_from_last(last if last not in ("Нет данных",) else None, interval)
        # map emoji status if present
        if "🟢" in status_cell:
            status = "ok"
        elif "🟡" in status_cell:
            status = "plan"
        elif "🔴" in status_cell:
            status = "overdue"
        else:
            status = computed
        rows.append({
            "id": _slug(name),
            "name": name,
            "interval": interval,
            "last_date": None if last in ("Нет данных", "—", "-") else last,
            "status": status,
            "status_label": {
                "ok": "Актуально",
                "plan": "Запланировать",
                "overdue": "Пора",
            }.get(status, status),
            "due_in_days": None,
        })
        if rows[-1]["last_date"]:
            try:
                d = date.fromisoformat(rows[-1]["last_date"][:10])
                next_due = d.toordinal() + _interval_days(interval)
                rows[-1]["due_in_days"] = next_due - date.today().toordinal()
            except ValueError:
                pass
    return rows


def _render_checkups_md(meta: dict, rows: list[dict]) -> str:
    lines = [
        "| Обследование | Интервал | Последний раз | Статус |",
        "| :--- | :--- | :--- | :--- |",
    ]
    emoji = {"ok": "🟢 Актуально", "plan": "🟡 Запланировать", "overdue": "🔴 Пора!"}
    for r in rows:
        last = r.get("last_date") or "Нет данных"
        st = emoji.get(r.get("status", "plan"), r.get("status_label", ""))
        lines.append(f"| {r['name']} | {r['interval']} | {last} | {st} |")
    return "\n".join(lines) + "\n"


# ── helpers: complaints ───────────────────────────────────────────────────


def _load_complaints(store: MDStorage) -> list[dict]:
    meta, _ = _read_meta(store, COMPLAINTS_PATH)
    entries = meta.get("entries") or []
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


def _save_complaints(store: MDStorage, entries: list[dict], body: str = "") -> None:
    meta = {
        "trust_tier": "unverified",
        "date": _today(),
        "tags": ["жалобы", "копилка"],
        "source": "mini-app",
        "entries": entries,
    }
    if not body:
        body = (
            "# 🪙 Копилка жалоб\n\n"
            "Симптомы, которые копятся до следующего визита к врачу.\n"
            "Не является диагнозом — только ваша фиксация.\n"
        )
    store.write(COMPLAINTS_PATH, meta, body)


# ── helpers: labs / navigator / previsit ──────────────────────────────────


def _is_abnormal_flag(flag: object) -> bool:
    """Recognize agent-written lab flags (emoji + Latin short codes).

    Agent dual-write uses ✅ / ⚠️ / 🔴 in parameters[].flag (see lab YAML).
    Older/API-style uses high|low|h|l|↑|↓|abnormal|critical.
    """
    if flag is None:
        return False
    raw = str(flag).strip()
    if not raw:
        return False
    # Normal markers (agent + Latin)
    normal = {
        "✅", "✔", "✓", "ok", "normal", "n", "норм", "в норме", "—", "-",
    }
    if raw.lower() in normal or raw in normal:
        return False
    # Explicit abnormal markers used in sasha-health data files
    abnormal_exact = {
        "🔴", "⚠️", "⚠", "↑", "↓", "⬆", "⬇", "🔺", "🔻",
        "high", "low", "h", "l", "abnormal", "critical", "out", "panic",
        "выше", "ниже", "повышен", "понижен",
    }
    low = raw.lower()
    if raw in abnormal_exact or low in abnormal_exact:
        return True
    # Any red/warning emoji or arrow remaining
    if any(ch in raw for ch in ("🔴", "⚠", "↑", "↓", "⬆", "⬇")):
        return True
    if low.startswith(("high", "low", "abn", "crit")):
        return True
    return False


def _scan_lab_flags(store: MDStorage) -> list[dict]:
    """Pull abnormal parameters from Анализы bundles."""
    cat = store.base_dir / "Анализы"
    if not cat.is_dir():
        return []
    abnormal: list[dict] = []
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
                flag = p.get("flag")
                if _is_abnormal_flag(flag):
                    abnormal.append({
                        "date": meta.get("date", ""),
                        "test": meta.get("test_name") or bundle.name,
                        "name": p.get("name"),
                        "value": p.get("value"),
                        "unit": p.get("unit"),
                        "ref_range": p.get("ref_range"),
                        "flag": str(flag) if flag is not None else "",
                    })
    return abnormal


def _route_symptoms(text: str) -> list[dict]:
    t = text.lower()
    hits: list[dict] = []
    for rule in NAV_MAP:
        score = sum(1 for k in rule["keywords"] if k in t)
        if score:
            hits.append({**rule, "score": score})
    hits.sort(key=lambda x: x["score"], reverse=True)
    if not hits:
        # default to therapist
        base = next(r for r in NAV_MAP if r["specialty"].startswith("Терапевт"))
        return [{**base, "score": 0}]
    return hits


def _build_previsit_prompt(
    *,
    specialty: str,
    doctor: str | None,
    institution: str | None,
    profile: dict,
    body: str,
    complaints: list[dict],
    labs: list[dict],
    strategy_body: str,
) -> str:
    name = profile.get("full_name") or "Пациент"
    dob = profile.get("birth_date") or ""
    diagnoses = profile.get("diagnoses") or []
    allergies = profile.get("allergies") or []
    diag_lines = []
    for d in diagnoses:
        if isinstance(d, dict):
            diag_lines.append(f"• {d.get('name', '')} ({d.get('date', '')}) {d.get('status', '')}")
        else:
            diag_lines.append(f"• {d}")

    open_c = [c for c in complaints if not c.get("resolved")]
    c_lines = [f"• [{c.get('date')}] sev={c.get('severity')}: {c.get('text')}" for c in open_c[:20]]
    lab_lines = [
        f"• {l.get('name')}: {l.get('value')} {l.get('unit') or ''} "
        f"(норма {l.get('ref_range') or '—'}, {l.get('date')})"
        for l in labs[:25]
    ]
    anthropo = (body or "").strip().splitlines()
    anthropo_s = anthropo[0] if anthropo else ""

    prompt = f"""Ты — медицинский редактор. Сгенерируй ОДИН лист «Лист 1 — ВРАЧУ» на русском
для распечатки перед приёмом. Мягкий язык, без императивов и без диагнозов от ИИ.
Формат: markdown, одна страница, чекбоксы ☐ только для исследований вне нормы.

КОНТЕКСТ ПАЦИЕНТА
ФИО: {name}
ДР: {dob}
Антропометрия: {anthropo_s}
Специалист: {specialty}
Врач: {doctor or "—"}
Учреждение: {institution or "—"}

ДИАГНОЗЫ (из карты пациента, не интерпретировать заново):
{chr(10).join(diag_lines) or "• (нет в карте)"}

АЛЛЕРГИИ: {", ".join(allergies) if allergies else "не указаны"}

НАКОПЛЕННЫЕ ЖАЛОБЫ (самоотчёт пациента):
{chr(10).join(c_lines) or "• (копилка пуста)"}

РЕЗУЛЬТАТЫ ВНЕ НОРМЫ (из файлов анализов):
{chr(10).join(lab_lines) or "• (нет помеченных отклонений в файлах)"}

ФРАГМЕНТ СТРАТЕГИИ (если релевантно специалисту — используй мягко):
{(strategy_body or "")[:1800]}

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
    return prompt.strip() + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/api/overview")
async def overview(_user: dict = require_auth):
    """Dashboard aggregate from real markdown files."""
    store = _store()
    vitals = _list_vitals(store, limit=30)
    bp_series = [v for v in vitals if v.get("bp")]
    weight_series = [v for v in vitals if v.get("weight_kg") is not None]
    last_bp = bp_series[0] if bp_series else None
    last_w = weight_series[0] if weight_series else None
    if last_w is None:
        pw = _profile_weight(store)
        if pw is not None:
            last_w = {"weight_kg": pw, "date": None, "source": "карточка.md"}

    meta, body = _read_meta(store, PROFILE_PATH)
    checkups = _parse_checkups_table(_read_meta(store, CHECKUPS_PATH)[1])
    overdue = [c for c in checkups if c["status"] == "overdue"]
    complaints = [c for c in _load_complaints(store) if not c.get("resolved")]

    ins_meta, _ = _read_meta(store, INSURANCE_PATH)
    policies = ins_meta.get("policies") or []
    policy = policies[0] if policies else None

    return {
        "patient": {
            "full_name": meta.get("full_name"),
            "birth_date": meta.get("birth_date"),
            "short_name": (meta.get("full_name") or "Пациент").split()[1]
            if meta.get("full_name") and len((meta.get("full_name") or "").split()) > 1
            else (meta.get("full_name") or "Пациент").split()[0],
            "diagnoses": meta.get("diagnoses") or [],
            "allergies": meta.get("allergies") or [],
            "summary_line": (body or "").strip().splitlines()[0] if body else "",
        },
        "vitals": {
            "last_bp": last_bp,
            "last_weight": last_w,
            "bp_count": len(bp_series),
            "weight_count": len(weight_series),
        },
        "checkups": {
            "total": len(checkups),
            "overdue": len(overdue),
            "items": checkups[:6],
        },
        "complaints_open": len(complaints),
        "insurance": policy,
        "disclaimer": (
            "Не является медицинской диагностикой. Для решений по лечению "
            "обращайтесь к врачу."
        ),
    }


@router.get("/api/vitals")
async def get_vitals(
    limit: int = Query(default=60, ge=1, le=200),
    _user: dict = require_auth,
):
    store = _store()
    items = _list_vitals(store, limit=limit)
    return {"count": len(items), "items": items, "tracked": ["bp", "weight_kg"]}


@router.post("/api/vitals", status_code=201)
async def post_vital(body: VitalCreate, _user: dict = require_auth):
    if body.bp is None and body.weight_kg is None:
        raise HTTPException(400, "Provide bp and/or weight_kg")
    if body.bp and _parse_bp(body.bp) is None:
        raise HTTPException(400, "bp must look like 120/80")

    store = _store()
    today = _today()
    ts = datetime.now().strftime("%H%M%S")
    kind = "ad" if body.bp else "ves"
    if body.bp and body.weight_kg is not None:
        kind = "ad_ves"
    filename = f"{today}_{kind}_{ts}.md"
    filepath = f"{QUICK_DIR}/{filename}"

    meta: dict[str, Any] = {
        "date": today,
        "tags": ["витал", "mini-app"],
        "trust_tier": "unverified",
        "source": "mini-app",
    }
    if body.bp:
        meta["bp"] = body.bp
        meta["tags"].append("давление")
    if body.weight_kg is not None:
        meta["weight_kg"] = body.weight_kg
        meta["tags"].append("вес")
    if body.when:
        meta["when"] = body.when
    if body.notes:
        meta["notes"] = body.notes

    store.write(filepath, meta, content=body.notes or "")
    logger.info("Vital logged: %s", meta)
    return {"ok": True, "path": filepath, **meta}


@router.get("/api/checkups")
async def get_checkups(_user: dict = require_auth):
    store = _store()
    meta, body = _read_meta(store, CHECKUPS_PATH)
    if not body and not meta:
        raise HTTPException(404, "чекапы.md not found")
    items = _parse_checkups_table(body)
    summary = {
        "ok": sum(1 for i in items if i["status"] == "ok"),
        "plan": sum(1 for i in items if i["status"] == "plan"),
        "overdue": sum(1 for i in items if i["status"] == "overdue"),
    }
    return {"count": len(items), "summary": summary, "items": items}


@router.patch("/api/checkups/{slug}")
async def patch_checkup(slug: str, body: CheckupPatch, _user: dict = require_auth):
    store = _store()
    meta, content = _read_meta(store, CHECKUPS_PATH)
    items = _parse_checkups_table(content)
    found = None
    for it in items:
        if it["id"] == slug:
            found = it
            break
    if not found:
        raise HTTPException(404, f"checkup '{slug}' not found")
    if body.last_date:
        found["last_date"] = body.last_date
    if body.status:
        found["status"] = body.status
    else:
        found["status"] = _status_from_last(found.get("last_date"), found["interval"])
    new_body = _render_checkups_md(meta, items)
    meta = meta or {"trust_tier": "trusted", "date": _today(), "tags": ["чекапы"]}
    meta["date"] = _today()
    store.write(CHECKUPS_PATH, meta, new_body)
    return found


@router.get("/api/complaints")
async def get_complaints(
    include_resolved: bool = False,
    _user: dict = require_auth,
):
    store = _store()
    entries = _load_complaints(store)
    if not include_resolved:
        entries = [e for e in entries if not e.get("resolved")]
    return {"count": len(entries), "items": entries}


@router.post("/api/complaints", status_code=201)
async def post_complaint(body: ComplaintCreate, _user: dict = require_auth):
    store = _store()
    entries = _load_complaints(store)
    routes = _route_symptoms(body.text)
    top = routes[0] if routes else None
    entry = {
        "id": str(uuid.uuid4())[:8],
        "date": _today(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "text": body.text.strip(),
        "severity": body.severity,
        "tags": body.tags,
        "specialty_hint": body.specialty_hint or (top["specialty"] if top else None),
        "navigator": [
            {
                "specialty": r["specialty"],
                "covered": r["covered"],
                "note": r["note"],
                "score": r["score"],
            }
            for r in routes[:3]
        ],
        "resolved": False,
    }
    entries.insert(0, entry)
    _save_complaints(store, entries)
    return entry


@router.delete("/api/complaints/{complaint_id}")
async def delete_complaint(
    complaint_id: str,
    hard: bool = False,
    _user: dict = require_auth,
):
    store = _store()
    entries = _load_complaints(store)
    new_entries: list[dict] = []
    found = False
    for e in entries:
        if e.get("id") == complaint_id:
            found = True
            if hard:
                continue
            e = {**e, "resolved": True, "resolved_at": _today()}
            new_entries.append(e)
        else:
            new_entries.append(e)
    if not found:
        raise HTTPException(404, "complaint not found")
    _save_complaints(store, new_entries)
    return {"ok": True, "hard": hard}


@router.get("/api/navigator")
async def navigator(
    q: Optional[str] = Query(default=None, description="Free-text symptoms"),
    _user: dict = require_auth,
):
    store = _store()
    complaints = [c for c in _load_complaints(store) if not c.get("resolved")]
    blob = q or " ".join(c.get("text", "") for c in complaints)
    routes = _route_symptoms(blob) if blob.strip() else []
    ins_meta, ins_body = _read_meta(store, INSURANCE_PATH)
    policies = ins_meta.get("policies") or []
    return {
        "query": q,
        "from_open_complaints": not bool(q) and bool(complaints),
        "routes": [
            {
                "specialty": r["specialty"],
                "score": r.get("score", 0),
                "covered": r["covered"],
                "note": r["note"],
                "prep": r.get("prep") or [],
            }
            for r in routes
        ],
        "insurance": {
            "policies": policies,
            "not_covered": NOT_COVERED,
            "body_excerpt": (ins_body or "")[:1200],
        },
        "open_complaints": len(complaints),
    }


@router.post("/api/previsit")
async def previsit(body: PrevisitRequest, _user: dict = require_auth):
    store = _store()
    profile, pbody = _read_meta(store, PROFILE_PATH)
    complaints = _load_complaints(store)
    if not body.include_open_complaints:
        complaints = []
    labs = _scan_lab_flags(store) if body.include_abnormal_labs else []
    _, strategy_body = _read_meta(store, STRATEGY_PATH)
    prompt = _build_previsit_prompt(
        specialty=body.specialty,
        doctor=body.doctor,
        institution=body.institution,
        profile=profile,
        body=pbody,
        complaints=complaints,
        labs=labs,
        strategy_body=strategy_body,
    )
    return {
        "specialty": body.specialty,
        "doctor": body.doctor,
        "prompt": prompt,
        "meta": {
            "complaints_used": len([c for c in complaints if not c.get("resolved")]),
            "labs_used": len(labs),
            "zero_api": True,
            "hint": "Скопируйте промпт → вставьте в Gemini → получите Лист 1 для врача.",
        },
    }
