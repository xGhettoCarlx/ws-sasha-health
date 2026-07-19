#!/usr/bin/env python3
"""Belgosstrakh (Белгосстрах) DMS medical-help application submitter.

Target form (public cabinet):
  https://my.bgs.by/UserCabinet/CallReferenceOnline.aspx
  «Заявка на организацию медицинской помощи» (ДМС)

Architecture decision (2026-07-19 probe):
  - Form is ASP.NET WebForms with empty ViewState key session + reCAPTCHA v3
    sitekey ``6Lee8KMUAAAAAKVeRTRlRBVk8s9MnEMcsPCrRa-7`` action CreateCallReferenceOnline.
  - Pure HTTP works for dry-run / payload validation; live submit needs either
    a browser (Playwright executes grecaptcha) or a pre-minted captcha token.
  - Optional personal-cabinet login via JSON endpoints:
      POST UCBNLogin.aspx/LoginValidate  then  UCBNLogin.aspx/Login
    (may require SMS time_code 2FA — tool returns ``needs_2fa``).

Usage:
  python tools/belgosstrakh_submit.py --dry-run \\
    --full-name "Иванов Иван Иванович" \\
    --institution "Новамед" --specialty "Кардиолог" \\
    --doctor "Спицарева О.Е." --datetime "12.08.2026 10:30" \\
    --complaint "Пульс 80-85, нужны Эхо-КГ и Холтер"

  python tools/belgosstrakh_submit.py --live --engine playwright ...

Env (.env / process):
  BGS_LOGIN, BGS_PASSWORD          — optional cabinet login
  BGS_POLICY_SERIES, BGS_POLICY_NUMBER
  BGS_PHONE, BGS_EMAIL, BGS_BIRTHDAY  (DD.MM.YYYY)
  BGS_CITY (default Могилёв)
  BGS_FULL_NAME                    — default FIO
  BGS_ENGINE=http|playwright
  BGS_HEADLESS=1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# ── optional project root on sys.path ─────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

FORM_URL = "https://my.bgs.by/UserCabinet/CallReferenceOnline.aspx"
LOGIN_URL = "https://my.bgs.by/UserCabinet/UCBNLogin.aspx"
LOGIN_VALIDATE = "https://my.bgs.by/UserCabinet/UCBNLogin.aspx/LoginValidate"
LOGIN_DO = "https://my.bgs.by/UserCabinet/UCBNLogin.aspx/Login"
RECAPTCHA_SITEKEY = "6Lee8KMUAAAAAKVeRTRlRBVk8s9MnEMcsPCrRa-7"
RECAPTCHA_ACTION = "CreateCallReferenceOnline"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# ASP.NET control names (ctl00$...$)
P = "ctl00$cphFormContent$WUC_UCBNCallReferenceOnline$"
FIELD = {
    "last_name": f"{P}TB_CallReferenceOnline_Body_Form_PersonLastName",
    "first_name": f"{P}TB_CallReferenceOnline_Body_Form_PersonFirstName",
    "patronymic": f"{P}TB_CallReferenceOnline_Body_Form_PersonPatronymic",
    "birthday": f"{P}RMTB_CallReferenceOnline_Body_Form_PersonBirthday",
    "phone": f"{P}RMTB_CallReferenceOnline_Body_Form_PersonPhoneNumber",
    "email": f"{P}TB_CallReferenceOnline_Body_Form_PersonEmail",
    "policy_series": f"{P}TB_CallReferenceOnline_Body_Form_BSOSeries",
    "policy_number": f"{P}TB_CallReferenceOnline_Body_Form_BSONumber",
    "city": f"{P}TB_CallReferenceOnline_Body_Form_AppointmentCity",
    "service": f"{P}TB_CallReferenceOnline_Body_Form_AppointmentService",
    "datetime_desc": f"{P}TB_CallReferenceOnline_Body_Form_AppointmentDateDescription",
    "description": f"{P}TB_CallReferenceOnline_Body_Form_ReferenceDescription",
    "captcha_token": f"{P}HF_Btn_ML_CallReferenceOnline_Body_Form_Send_Token",
    "send_button": f"{P}Btn_ML_CallReferenceOnline_Body_Form_Send",
}
# DOM ids for Playwright (underscore form of UniqueID)
DOM_ID = {
    "last_name": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_PersonLastName",
    "first_name": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_PersonFirstName",
    "patronymic": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_PersonPatronymic",
    "birthday": "ctl00_cphFormContent_WUC_UCBNCallReferenceOnline_RMTB_CallReferenceOnline_Body_Form_PersonBirthday",
    "phone": "ctl00_cphFormContent_WUC_UCBNCallReferenceOnline_RMTB_CallReferenceOnline_Body_Form_PersonPhoneNumber",
    "email": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_PersonEmail",
    "policy_series": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_BSOSeries",
    "policy_number": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_BSONumber",
    "city": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_AppointmentCity",
    "service": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_AppointmentService",
    "datetime_desc": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_AppointmentDateDescription",
    "description": "cphFormContent_WUC_UCBNCallReferenceOnline_TB_CallReferenceOnline_Body_Form_ReferenceDescription",
    "send_button": "Btn_ML_CallReferenceOnline_Body_Form_Send",
}


# ── data models ───────────────────────────────────────────────────────────


@dataclass
class SubmitRequest:
    full_name: str
    institution: str
    specialty: str
    doctor: str = ""
    datetime_pref: str = ""
    complaint: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    birthday: str = ""
    policy_series: str = ""
    policy_number: str = ""
    login: str = ""
    password: str = ""
    captcha_token: str = ""
    engine: str = "http"  # http | playwright
    headless: bool = True
    live: bool = False
    timeout_s: float = 60.0

    def split_fio(self) -> Tuple[str, str, str]:
        parts = [p for p in re.split(r"\s+", (self.full_name or "").strip()) if p]
        if len(parts) >= 3:
            return parts[0], parts[1], " ".join(parts[2:])
        if len(parts) == 2:
            return parts[0], parts[1], ""
        if len(parts) == 1:
            return parts[0], "", ""
        return "", "", ""

    def service_text(self) -> str:
        bits = [self.specialty.strip()]
        if self.doctor.strip():
            bits.append(self.doctor.strip())
        if self.institution.strip():
            bits.append(f"учр. {self.institution.strip()}")
        return ", ".join(b for b in bits if b)

    def description_text(self) -> str:
        lines = []
        if self.complaint.strip():
            lines.append(self.complaint.strip())
        if self.doctor.strip():
            lines.append(f"Врач: {self.doctor.strip()}")
        if self.institution.strip():
            lines.append(f"Учреждение: {self.institution.strip()}")
        if self.specialty.strip():
            lines.append(f"Специальность: {self.specialty.strip()}")
        return "\n".join(lines) if lines else self.service_text()


@dataclass
class SubmitResult:
    ok: bool
    status: str  # success | dry_run | error | needs_captcha | needs_2fa | needs_playwright
    message: str
    confirmation_code: Optional[str] = None
    engine: str = "http"
    http_status: Optional[int] = None
    redirect_url: Optional[str] = None
    payload_preview: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── helpers ───────────────────────────────────────────────────────────────


def load_dotenv_files() -> None:
    """Load .env from app root and hermes profile without overriding existing env."""
    candidates = [
        _ROOT / ".env",
        Path.home() / ".hermes" / "profiles" / "sasha-health" / ".env",
        Path.home() / ".hermes" / ".env",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        except OSError:
            continue


def format_phone_by(phone: str) -> str:
    """Normalize to Belgosstrakh mask +375 (XX) XXX-XX-XX when possible."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("80") and len(digits) == 11:
        digits = "375" + digits[2:]
    if digits.startswith("375") and len(digits) == 12:
        return f"+{digits[:3]} ({digits[3:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
    if len(digits) == 9:  # 29xxxxxxx
        return f"+375 ({digits[0:2]}) {digits[2:5]}-{digits[5:7]}-{digits[7:9]}"
    return phone.strip() if phone else ""


def format_birthday(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", raw):
        return raw
    # ISO
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return raw


def request_from_env_and_args(**overrides: Any) -> SubmitRequest:
    load_dotenv_files()
    base = SubmitRequest(
        full_name=os.environ.get("BGS_FULL_NAME", ""),
        institution="",
        specialty="",
        city=os.environ.get("BGS_CITY", "Могилёв"),
        phone=os.environ.get("BGS_PHONE", ""),
        email=os.environ.get("BGS_EMAIL", ""),
        birthday=os.environ.get("BGS_BIRTHDAY", ""),
        policy_series=os.environ.get("BGS_POLICY_SERIES", ""),
        policy_number=os.environ.get("BGS_POLICY_NUMBER", ""),
        login=os.environ.get("BGS_LOGIN", "") or os.environ.get("BELGOSSTRAKH_LOGIN", ""),
        password=os.environ.get("BGS_PASSWORD", "") or os.environ.get("BELGOSSTRAKH_PASSWORD", ""),
        engine=os.environ.get("BGS_ENGINE", "http"),
        headless=os.environ.get("BGS_HEADLESS", "1") not in ("0", "false", "False"),
    )
    for k, v in overrides.items():
        if v is None:
            continue
        if hasattr(base, k):
            setattr(base, k, v)
    return base


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: Dict[str, str] = {}
        self._select: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        d = {k: (v or "") for k, v in attrs}
        if tag == "input":
            name = d.get("name")
            if not name:
                return
            typ = (d.get("type") or "text").lower()
            if typ in ("checkbox", "radio") and "checked" not in d:
                return
            if typ in ("submit", "button", "image") and name not in self.fields:
                # keep empty; we set send button ourselves
                return
            self.fields[name] = d.get("value", "")
        elif tag == "textarea":
            name = d.get("name")
            if name:
                self.fields[name] = ""
                self._select = name  # reuse buffer for textarea content
        elif tag == "select":
            self._select = d.get("name")

    def handle_data(self, data: str) -> None:
        if self._select and self._select in self.fields:
            # textarea body
            if not self.fields[self._select]:
                self.fields[self._select] = data

    def handle_endtag(self, tag: str) -> None:
        if tag in ("textarea", "select"):
            self._select = None


def parse_form_fields(html: str) -> Dict[str, str]:
    p = _FormParser()
    p.feed(html)
    return p.fields


def build_payload(req: SubmitRequest, form_fields: Dict[str, str]) -> Dict[str, str]:
    last, first, patronymic = req.split_fio()
    data = dict(form_fields)
    data[FIELD["last_name"]] = last
    data[FIELD["first_name"]] = first
    data[FIELD["patronymic"]] = patronymic
    # Prefer provided values; do not keep RadMasked placeholder garbage
    bday = format_birthday(req.birthday)
    data[FIELD["birthday"]] = bday if bday else ""
    phone = format_phone_by(req.phone)
    data[FIELD["phone"]] = phone if phone else ""
    data[FIELD["email"]] = req.email or ""
    data[FIELD["policy_series"]] = req.policy_series or ""
    data[FIELD["policy_number"]] = req.policy_number or ""
    data[FIELD["city"]] = req.city or "Могилёв"
    data[FIELD["service"]] = req.service_text()
    data[FIELD["datetime_desc"]] = req.datetime_pref or ""
    data[FIELD["description"]] = req.description_text()
    if req.captcha_token:
        data[FIELD["captcha_token"]] = req.captcha_token
    # ASP.NET postback target for send button
    data["__EVENTTARGET"] = "Btn_ML_CallReferenceOnline_Body_Form_Send"
    data["__EVENTARGUMENT"] = ""
    # Also include button name (some handlers check it)
    data[FIELD["send_button"]] = "Сохранить заявление"
    return data


def payload_preview(data: Dict[str, str]) -> Dict[str, str]:
    """Human-readable subset for agent logs (no secrets beyond form)."""
    inv = {v: k for k, v in FIELD.items()}
    out = {}
    for name, val in data.items():
        if name.startswith("__") and name not in ("__EVENTTARGET",):
            continue
        key = inv.get(name, name)
        if key in ("password",) or "Password" in name:
            continue
        if len(val) > 200:
            val = val[:200] + "…"
        out[key] = val
    return out


def extract_confirmation(html: str) -> Tuple[Optional[str], str]:
    """Return (code_or_none, message)."""
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    # common success phrases
    if re.search(r"успешн|принято|зарегистрирован|отправлен", text, re.I):
        m = re.search(
            r"(номер|код|заявк[аи].{0,20}№?\s*)([A-Z0-9\-/]{4,})",
            text,
            re.I,
        )
        code = m.group(2) if m else None
        # grab a short success line
        for line in text.splitlines():
            line = line.strip()
            if re.search(r"успешн|принято|зарегистрирован", line, re.I) and 10 < len(line) < 200:
                return code, line
        return code, "Заявка принята (успех по маркерам страницы)"
    err = None
    for line in text.splitlines():
        line = line.strip()
        if re.search(r"ошибк|некоррект|обязательн|captcha|капч", line, re.I) and 5 < len(line) < 200:
            err = line
            break
    return None, err or "Не удалось подтвердить успех по HTML-ответу"


# ── HTTP engine ───────────────────────────────────────────────────────────


def _client(timeout: float) -> "httpx.Client":
    if httpx is None:
        raise RuntimeError("httpx not installed")
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ru-RU,ru;q=0.9"},
    )


def login_cabinet(client: "httpx.Client", login: str, password: str) -> SubmitResult:
    """Optional personal-cabinet login via JSON ASMX-style methods."""
    if not login or not password:
        return SubmitResult(False, "error", "login/password empty", engine="http")
    # warm cookies
    client.get(LOGIN_URL)
    headers = {"Content-Type": "application/json; charset=utf-8"}
    body = json.dumps({"userName": login, "password": password})
    r = client.post(LOGIN_VALIDATE, content=body, headers=headers)
    if r.status_code != 200:
        return SubmitResult(
            False,
            "error",
            f"LoginValidate HTTP {r.status_code}",
            engine="http",
            http_status=r.status_code,
            raw={"body": r.text[:500]},
        )
    try:
        wrapper = r.json()
        payload = json.loads(wrapper.get("d") or "{}")
    except Exception as e:
        return SubmitResult(False, "error", f"LoginValidate parse: {e}", engine="http")

    code = payload.get("code")
    if code != 0:
        return SubmitResult(
            False,
            "error",
            str(payload.get("message") or "LoginValidate failed"),
            engine="http",
            raw=payload,
        )
    if payload.get("time_code") is True:
        return SubmitResult(
            False,
            "needs_2fa",
            "Личный кабинет требует time_code (SMS/2FA). "
            "Пройдите 2FA вручную или отключите для API-логина.",
            engine="http",
            raw=payload,
        )

    r2 = client.post(LOGIN_DO, content=body, headers=headers)
    try:
        wrapper2 = r2.json()
        payload2 = json.loads(wrapper2.get("d") or "{}")
    except Exception as e:
        return SubmitResult(False, "error", f"Login parse: {e}", engine="http")
    if payload2.get("code") != 0:
        return SubmitResult(
            False,
            "error",
            str(payload2.get("message") or "Login failed"),
            engine="http",
            raw=payload2,
        )
    return SubmitResult(
        True,
        "success",
        "Login OK",
        engine="http",
        redirect_url=payload2.get("redirect_url"),
        raw=payload2,
    )


def submit_http(req: SubmitRequest) -> SubmitResult:
    if httpx is None:
        return SubmitResult(False, "error", "httpx is required", engine="http")

    with _client(req.timeout_s) as client:
        if req.login and req.password:
            lr = login_cabinet(client, req.login, req.password)
            if lr.status == "needs_2fa":
                return lr
            if not lr.ok:
                # login optional for public form — warn but continue
                pass

        r = client.get(FORM_URL)
        if r.status_code != 200:
            return SubmitResult(
                False,
                "error",
                f"GET form HTTP {r.status_code}",
                engine="http",
                http_status=r.status_code,
            )
        fields = parse_form_fields(r.text)
        data = build_payload(req, fields)
        preview = payload_preview(data)

        if not req.live:
            return SubmitResult(
                True,
                "dry_run",
                "Dry-run: payload built, form reachable. Pass --live to submit.",
                engine="http",
                http_status=r.status_code,
                payload_preview=preview,
                raw={
                    "form_url": FORM_URL,
                    "fields_seen": len(fields),
                    "recaptcha_sitekey": RECAPTCHA_SITEKEY,
                    "note": "Live HTTP requires captcha_token or use --engine playwright",
                },
            )

        if not req.captcha_token:
            return SubmitResult(
                False,
                "needs_captcha",
                "Live HTTP submit requires reCAPTCHA v3 token "
                f"(sitekey {RECAPTCHA_SITEKEY}). Use --engine playwright or --captcha-token.",
                engine="http",
                payload_preview=preview,
            )

        data[FIELD["captcha_token"]] = req.captcha_token
        post = client.post(
            FORM_URL,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://my.bgs.by",
                "Referer": FORM_URL,
            },
        )
        code, msg = extract_confirmation(post.text)
        ok = code is not None or "успех" in msg.lower() or "принят" in msg.lower()
        return SubmitResult(
            ok=ok,
            status="success" if ok else "error",
            message=msg,
            confirmation_code=code,
            engine="http",
            http_status=post.status_code,
            payload_preview=preview,
            raw={"response_len": len(post.text), "url": str(post.url)},
        )


# ── Playwright engine ─────────────────────────────────────────────────────


def submit_playwright(req: SubmitRequest) -> SubmitResult:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return SubmitResult(
            False,
            "needs_playwright",
            "Playwright not installed. "
            "Run: pip install playwright && playwright install chromium",
            engine="playwright",
        )

    last, first, patronymic = req.split_fio()
    preview = {
        "last_name": last,
        "first_name": first,
        "patronymic": patronymic,
        "service": req.service_text(),
        "datetime": req.datetime_pref,
        "city": req.city,
        "complaint": (req.complaint or "")[:120],
    }

    if not req.live:
        # still verify browser can open form
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=req.headless)
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(FORM_URL, wait_until="domcontentloaded", timeout=int(req.timeout_s * 1000))
                title = page.title()
                browser.close()
            return SubmitResult(
                True,
                "dry_run",
                f"Dry-run Playwright OK, page title: {title}",
                engine="playwright",
                payload_preview=preview,
            )
        except Exception as e:
            return SubmitResult(
                False,
                "error",
                f"Playwright dry-run failed: {e}",
                engine="playwright",
                raw={"trace": traceback.format_exc()[-800:]},
            )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=req.headless)
            context = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
            page = context.new_page()

            # optional login
            if req.login and req.password:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=int(req.timeout_s * 1000))
                page.fill("#cphFormContent_UCBNLogin_TB_Login", req.login)
                page.fill("#cphFormContent_ucbnPassword_tbPassword", req.password)
                page.click("#btnLogin")
                page.wait_for_timeout(2500)
                content = page.content()
                if "time_code" in content.lower() or "код" in page.inner_text("body")[:500].lower():
                    # heuristic: 2FA wizard visible
                    if page.is_visible("#cphFormContent_ucbnTimeCodeWizard_tbTimeCode"):
                        browser.close()
                        return SubmitResult(
                            False,
                            "needs_2fa",
                            "Login requires time_code (2FA). Complete in headed browser.",
                            engine="playwright",
                        )

            page.goto(FORM_URL, wait_until="networkidle", timeout=int(req.timeout_s * 1000))

            def fill(dom_key: str, value: str) -> None:
                if not value:
                    return
                sel = f"#{DOM_ID[dom_key]}"
                page.fill(sel, value)

            fill("last_name", last)
            fill("first_name", first)
            fill("patronymic", patronymic)
            fill("birthday", format_birthday(req.birthday))
            fill("phone", format_phone_by(req.phone))
            fill("email", req.email)
            fill("policy_series", req.policy_series)
            fill("policy_number", req.policy_number)
            fill("city", req.city or "Могилёв")
            fill("service", req.service_text())
            fill("datetime_desc", req.datetime_pref)
            fill("description", req.description_text())

            # click send — triggers reCAPTCHA v3 then postback
            page.click(f"#{DOM_ID['send_button']}")
            page.wait_for_timeout(4000)
            # wait for either success panel or error
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            html = page.content()
            body_text = page.inner_text("body")
            browser.close()

        code, msg = extract_confirmation(html)
        if not code and re.search(r"успешн|принято|зарегистрирован", body_text, re.I):
            ok = True
            msg = msg if "успех" in msg.lower() or "принят" in msg.lower() else (
                re.search(r".{0,80}(успешн|принято|зарегистрирован).{0,80}", body_text, re.I)
                or type("M", (), {"group": lambda s, n=0: "Успех"})()
            ).group(0)
        else:
            ok = code is not None or bool(re.search(r"успешн|принято", msg, re.I))

        return SubmitResult(
            ok=ok,
            status="success" if ok else "error",
            message=str(msg)[:500],
            confirmation_code=code,
            engine="playwright",
            payload_preview=preview,
            raw={"body_snippet": body_text[:400]},
        )
    except Exception as e:
        return SubmitResult(
            False,
            "error",
            f"Playwright submit failed: {e}",
            engine="playwright",
            payload_preview=preview,
            raw={"trace": traceback.format_exc()[-1200:]},
        )


def submit(req: SubmitRequest) -> SubmitResult:
    """Main entry: validate required fields, dispatch engine."""
    missing = []
    if not (req.full_name or "").strip():
        missing.append("full_name")
    if not (req.specialty or "").strip() and not (req.doctor or "").strip():
        missing.append("specialty/doctor")
    if not (req.institution or "").strip():
        missing.append("institution")
    if missing:
        return SubmitResult(
            False,
            "error",
            f"Missing required fields: {', '.join(missing)}",
            engine=req.engine,
        )

    engine = (req.engine or "http").lower().strip()
    if engine == "playwright":
        return submit_playwright(req)
    # auto-upgrade to playwright for live if no captcha token
    if req.live and not req.captcha_token:
        pw = submit_playwright(req)
        if pw.status != "needs_playwright":
            return pw
        # fall through with needs_captcha message
        return SubmitResult(
            False,
            "needs_playwright",
            pw.message + " (HTTP live blocked by reCAPTCHA v3 without token)",
            engine="http",
        )
    return submit_http(req)


# ── CLI ───────────────────────────────────────────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Submit Belgosstrakh DMS medical-help application",
    )
    ap.add_argument("--full-name", default=None, help="ФИО")
    ap.add_argument("--institution", default=None, help="Учреждение")
    ap.add_argument("--specialty", default=None, help="Специальность / вид услуги")
    ap.add_argument("--doctor", default=None, help="ФИО врача")
    ap.add_argument("--datetime", dest="datetime_pref", default=None, help="Дата+время")
    ap.add_argument("--complaint", default=None, help="Жалоба / описание")
    ap.add_argument("--city", default=None)
    ap.add_argument("--phone", default=None)
    ap.add_argument("--email", default=None)
    ap.add_argument("--birthday", default=None, help="DD.MM.YYYY or YYYY-MM-DD")
    ap.add_argument("--policy-series", default=None)
    ap.add_argument("--policy-number", default=None)
    ap.add_argument("--login", default=None)
    ap.add_argument("--password", default=None)
    ap.add_argument("--captcha-token", default=None)
    ap.add_argument("--engine", choices=["http", "playwright"], default=None)
    ap.add_argument("--headed", action="store_true", help="Playwright headed mode")
    ap.add_argument("--live", action="store_true", help="Actually submit (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="Force dry-run")
    ap.add_argument("--json", action="store_true", help="Print JSON only")
    ap.add_argument("--timeout", type=float, default=60.0)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    live = bool(args.live) and not bool(args.dry_run)
    req = request_from_env_and_args(
        full_name=args.full_name,
        institution=args.institution,
        specialty=args.specialty,
        doctor=args.doctor,
        datetime_pref=args.datetime_pref,
        complaint=args.complaint,
        city=args.city,
        phone=args.phone,
        email=args.email,
        birthday=args.birthday,
        policy_series=args.policy_series,
        policy_number=args.policy_number,
        login=args.login,
        password=args.password,
        captcha_token=args.captcha_token,
        engine=args.engine,
        headless=not args.headed,
        live=live,
        timeout_s=args.timeout,
    )
    # CLI required fields if not from env
    if args.institution:
        req.institution = args.institution
    if args.specialty:
        req.specialty = args.specialty
    if args.full_name:
        req.full_name = args.full_name

    result = submit(req)
    out = result.to_dict()
    out["at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if result.ok or result.status in ("dry_run",):
        return 0
    if result.status in ("needs_captcha", "needs_2fa", "needs_playwright"):
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
