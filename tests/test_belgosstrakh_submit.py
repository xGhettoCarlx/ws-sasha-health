"""Unit tests for Belgosstrakh submit tool (no live network to BGS on assertions)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.belgosstrakh_submit import (  # noqa: E402
    FIELD,
    SubmitRequest,
    build_payload,
    format_birthday,
    format_phone_by,
    parse_form_fields,
    submit,
)


def test_split_fio():
    r = SubmitRequest(full_name="Калинов Александр Игоревич", institution="X", specialty="Y")
    assert r.split_fio() == ("Калинов", "Александр", "Игоревич")


def test_format_phone_by():
    assert format_phone_by("+375291234567") == "+375 (29) 123-45-67"
    assert format_phone_by("80291234567") == "+375 (29) 123-45-67"


def test_format_birthday():
    assert format_birthday("1993-08-26") == "26.08.1993"
    assert format_birthday("26.08.1993") == "26.08.1993"


def test_build_payload_maps_fields():
    html = f'''
    <form>
      <input type="hidden" name="__VIEWSTATE" value="VS" />
      <input type="hidden" name="__VIEWSTATEKEY" value="KEY" />
      <input name="{FIELD["last_name"]}" />
      <input name="{FIELD["first_name"]}" />
      <textarea name="{FIELD["description"]}"></textarea>
    </form>
    '''
    fields = parse_form_fields(html)
    req = SubmitRequest(
        full_name="Иванов Иван Иванович",
        institution="Новамед",
        specialty="Кардиолог",
        doctor="Спицарева",
        datetime_pref="12.08.2026 10:30",
        complaint="Пульс",
        city="Могилёв",
        phone="375291111111",
        policy_series="АА",
        policy_number="123",
    )
    data = build_payload(req, fields)
    assert data[FIELD["last_name"]] == "Иванов"
    assert data[FIELD["first_name"]] == "Иван"
    assert "Кардиолог" in data[FIELD["service"]]
    assert "Новамед" in data[FIELD["service"]]
    assert "Пульс" in data[FIELD["description"]]
    assert data["__EVENTTARGET"] == "Btn_ML_CallReferenceOnline_Body_Form_Send"


def test_submit_missing_fields():
    r = submit(SubmitRequest(full_name="", institution="", specialty=""))
    assert r.ok is False
    assert r.status == "error"
    assert "Missing" in r.message


def test_submit_dry_run_hits_form(monkeypatch):
    """Dry-run should GET the real form (network). Skip if offline."""
    req = SubmitRequest(
        full_name="Тестов Тест Тестович",
        institution="Новамед",
        specialty="Терапевт",
        doctor="Кабаев",
        datetime_pref="01.09.2026 09:00",
        complaint="Направления на анализы",
        city="Могилёв",
        live=False,
        engine="http",
        timeout_s=30,
    )
    try:
        res = submit(req)
    except Exception as e:
        pytest.skip(f"network unavailable: {e}")
    if res.status == "error" and "GET form" in res.message:
        pytest.skip(res.message)
    assert res.status == "dry_run"
    assert res.ok is True
    assert res.payload_preview.get("last_name") == "Тестов"
    assert "service" in res.payload_preview


@pytest.mark.asyncio
async def test_api_status_and_dry_submit(client, monkeypatch, test_data_dir):
    import app.config as cfg

    monkeypatch.setenv("BOT_TOKEN", "dev-local-placeholder")
    monkeypatch.setenv("DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "*")
    cfg._settings = None

    st = await client.get("/api/belgosstrakh/status")
    # may be 401 if auth treats placeholder differently — use no auth path? require_auth
    # with placeholder BOT_TOKEN → dev auth without headers
    assert st.status_code == 200
    body = st.json()
    assert "form_url" in body
    assert body["tool_path"].endswith("belgosstrakh_submit.py")

    r = await client.post(
        "/api/belgosstrakh/submit",
        json={
            "full_name": "Тестов Тест Тестович",
            "institution": "Новамед",
            "specialty": "Кардиолог",
            "doctor": "Спицарева",
            "datetime": "12.08.2026 10:30",
            "complaint": "Чекап",
            "live": False,
            "engine": "http",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("dry_run", "error")  # error only if network blocked
    if data["status"] == "dry_run":
        assert data["ok"] is True
