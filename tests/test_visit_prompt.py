"""Visit prompt builder + timeline trigger API."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from telegram_init_data import sign

from app.storage import MDStorage
from app.visit_prompt import build_visit_prompt_markdown, write_prompt_file

TEST_TOKEN = "12345:TEST_AUTH_TOKEN"
TEST_USER = {"id": 80101636, "first_name": "Sasha"}


def _reset_settings():
    import app.config as _cfg

    _cfg._settings = None


def _auth():
    data = {"user": TEST_USER}
    init_data = sign(data, TEST_TOKEN, datetime.now(timezone.utc))
    return {"Authorization": f"tma {init_data}"}


@pytest.fixture(autouse=True)
def _env(monkeypatch, test_data_dir):
    monkeypatch.setenv("BOT_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "*")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "80101636")
    _reset_settings()
    yield
    _reset_settings()


@pytest.fixture
def store(test_data_dir):
    # Multi-tenant: API MDStorage() resolves to data/users/<auth_user_id>/
    return MDStorage.for_user(TEST_USER["id"])


def _seed(store: MDStorage):
    store.write(
        "карточка.md",
        {
            "full_name": "Тестов Тест",
            "birth_date": "1990-01-01",
            "diagnoses": [
                {
                    "name": "Гипертония",
                    "date": "2026-01-01",
                    "status": "🔴",
                    "source": "Кабаев",
                }
            ],
            "allergies": ["пенициллин"],
            "trust_tier": "trusted",
            "date": "2026-01-01",
            "tags": [],
        },
        "180 см / 90 кг\n",
    )
    store.write(
        "копилка_жалоб.md",
        {
            "entries": [
                {
                    "id": "c1",
                    "date": "2026-07-01",
                    "text": "Пульс 85",
                    "severity": 6,
                    "resolved": False,
                    "specialty_hint": "Кардиолог",
                }
            ],
            "trust_tier": "unverified",
            "date": "2026-07-01",
            "tags": [],
        },
        "",
    )
    future = (date.today().replace(year=date.today().year + 1)).isoformat()
    store.write(
        "schedule/v-cardio.md",
        {
            "id": "v-cardio",
            "date": future,
            "visit_date": future,
            "doctor": "Спицарева (кардиолог)",
            "purpose": "Эхо-КГ",
            "status": "planned",
            "pipeline_stage": 2,
            "specialty": "Кардиология",
            "institution": "Новамед",
            "trust_tier": "unverified",
        },
        "",
    )


def test_build_markdown_includes_complaints_and_diagnoses(store):
    _seed(store)
    visit = {
        "id": "v-cardio",
        "doctor": "Спицарева",
        "specialty": "Кардиология",
        "purpose": "Чекап",
        "visit_date": "2027-01-01",
        "status": "planned",
    }
    md = build_visit_prompt_markdown(visit, store=store)
    assert "Пульс 85" in md
    assert "Гипертония" in md
    assert "GEMINI" in md
    assert "Лист 1" in md
    path = write_prompt_file(md, visit_id="v-cardio", store=store)
    assert path.is_file()
    assert path.stat().st_size > 100


@pytest.mark.asyncio
async def test_api_prompt_saves_file(client, store, monkeypatch):
    _seed(store)

    # Do not call real Telegram
    async def _no_send(*_a, **_k):
        return False

    monkeypatch.setattr("app.bot.send_document", _no_send)
    monkeypatch.setattr("app.bot.bot_token_usable", lambda: False)

    r = await client.post("/api/visits/v-cardio/prompt", headers=_auth(), json={})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["telegram_sent"] is False
    assert "export/prompts" in body["path"].replace("\\", "/")
    from pathlib import Path

    assert Path(body["path"]).is_file()


@pytest.mark.asyncio
async def test_api_prompt_rejects_completed(client, store):
    store.write(
        "schedule/v-done.md",
        {
            "id": "v-done",
            "date": "2020-01-01",
            "visit_date": "2020-01-01",
            "doctor": "X",
            "purpose": "done",
            "status": "completed",
            "trust_tier": "trusted",
        },
        "",
    )
    r = await client.post("/api/visits/v-done/prompt", headers=_auth(), json={})
    assert r.status_code == 400
