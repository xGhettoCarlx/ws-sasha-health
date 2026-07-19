"""API wrapper around tools/belgosstrakh_submit.py for agent / Mini App.

POST /api/belgosstrakh/submit
  body: full_name, institution, specialty, doctor, datetime_pref, complaint, ...
  query/body live=false by default (dry-run).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.auth import require_auth
from app.config import get_settings

router = APIRouter(prefix="/api/belgosstrakh", tags=["belgosstrakh"])

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS.parent))


class BelgosSubmitBody(BaseModel):
    full_name: str = Field(..., min_length=2, description="ФИО")
    institution: str = Field(..., min_length=1, description="Учреждение")
    specialty: str = Field(..., min_length=1, description="Специальность / вид услуги")
    doctor: str = Field(default="", description="ФИО врача")
    datetime_pref: str = Field(default="", alias="datetime", description="Дата+время")
    complaint: str = Field(default="", description="Жалоба")
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    birthday: Optional[str] = None
    policy_series: Optional[str] = None
    policy_number: Optional[str] = None
    live: bool = Field(default=False, description="True = real submit")
    engine: Optional[str] = Field(default=None, description="http | playwright")
    captcha_token: Optional[str] = None

    model_config = {"populate_by_name": True}


@router.post("/submit")
async def belgos_submit(body: BelgosSubmitBody, _user: dict = require_auth) -> dict[str, Any]:
    """Submit (or dry-run) a Belgosstrakh DMS medical-help application."""
    from tools.belgosstrakh_submit import SubmitRequest, submit  # type: ignore

    settings = get_settings()
    req = SubmitRequest(
        full_name=body.full_name or (settings.BGS_FULL_NAME or ""),
        institution=body.institution,
        specialty=body.specialty,
        doctor=body.doctor or "",
        datetime_pref=body.datetime_pref or "",
        complaint=body.complaint or "",
        city=body.city or settings.BGS_CITY or "Могилёв",
        phone=body.phone or settings.BGS_PHONE or "",
        email=body.email or settings.BGS_EMAIL or "",
        birthday=body.birthday or settings.BGS_BIRTHDAY or "",
        policy_series=body.policy_series or settings.BGS_POLICY_SERIES or "",
        policy_number=body.policy_number or settings.BGS_POLICY_NUMBER or "",
        login=settings.BGS_LOGIN or "",
        password=settings.BGS_PASSWORD or "",
        captcha_token=body.captcha_token or "",
        engine=(body.engine or settings.BGS_ENGINE or "http"),
        live=bool(body.live),
    )
    result = submit(req)
    out = result.to_dict()
    out["agent_hint"] = (
        "On success set visit insurance_warned=true via "
        "PATCH /api/schedule/{id}/insurance-warned"
    )
    return out


@router.get("/status")
async def belgos_status(_user: dict = require_auth) -> dict[str, Any]:
    """Credential / engine readiness (never returns secrets)."""
    s = get_settings()
    return {
        "form_url": "https://my.bgs.by/UserCabinet/CallReferenceOnline.aspx",
        "engine_default": s.BGS_ENGINE,
        "has_login": bool(s.BGS_LOGIN),
        "has_password": bool(s.BGS_PASSWORD),
        "has_policy": bool(s.BGS_POLICY_SERIES and s.BGS_POLICY_NUMBER),
        "has_phone": bool(s.BGS_PHONE),
        "has_full_name": bool(s.BGS_FULL_NAME),
        "city": s.BGS_CITY,
        "tool_path": str(_TOOLS / "belgosstrakh_submit.py"),
        "skill": "belgosstrakh-submit (sasha-health profile)",
    }
