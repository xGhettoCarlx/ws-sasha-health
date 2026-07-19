"""Tests for medical pipeline, timeline, and Trojan Horse API."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from telegram_init_data import sign

from app.storage import MDStorage

TEST_TOKEN = "12345:TEST_AUTH_TOKEN"
TEST_USER = {"id": 777, "first_name": "Alice"}


def _reset_settings():
    import app.config as _cfg

    _cfg._settings = None


def _auth(user=None):
    data = {"user": user or TEST_USER}
    init_data = sign(data, TEST_TOKEN, datetime.now(timezone.utc))
    return {"Authorization": f"tma {init_data}"}


@pytest.fixture(autouse=True)
def _env(monkeypatch, test_data_dir):
    monkeypatch.setenv("BOT_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "*")
    _reset_settings()
    yield
    _reset_settings()


@pytest.fixture
def store(test_data_dir):
    return MDStorage(base_dir=test_data_dir)


def _write_visit(store, vid: str, **meta):
    base = {
        "id": vid,
        "date": "2026-08-12",
        "doctor": "Dr Test",
        "purpose": "Check",
        "trust_tier": "unverified",
        "status": "planned",
        "pipeline_stage": 2,
        "insurance_warned": False,
    }
    base.update(meta)
    store.write(f"schedule/{vid}.md", base, "")


@pytest.mark.asyncio
async def test_pipeline_stages(client, store):
    _write_visit(store, "v1", pipeline_stage=1, status="completed", doctor="Therapist")
    _write_visit(store, "v2", pipeline_stage=2, status="planned", doctor="Cardio")

    r = await client.get("/api/pipeline", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert len(body["stages"]) == 5
    assert body["stages"][0]["stage"] == 1
    assert body["stages"][0]["counts"]["completed"] >= 1
    assert body["stages"][1]["counts"]["open"] >= 1
    assert body["total_visits"] >= 2


@pytest.mark.asyncio
async def test_timeline_future_past(client, store):
    past = date.today().replace(day=1).isoformat()
    future = "2099-01-15"
    _write_visit(
        store,
        "past1",
        date=past,
        visit_date=past,
        status="completed",
        pipeline_stage=1,
    )
    _write_visit(
        store,
        "fut1",
        date=future,
        visit_date=future,
        status="planned",
        pipeline_stage=2,
        insurance_warned=False,
    )

    r = await client.get("/api/timeline", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["future"] >= 1
    assert any(v.get("id") == "fut1" for v in body["future"])
    assert body["counts"]["insurance_unwarned_future"] >= 1


@pytest.mark.asyncio
async def test_insurance_warned_patch(client, store):
    _write_visit(store, "warn1", insurance_warned=False)

    r = await client.patch(
        "/api/schedule/warn1/insurance-warned",
        headers=_auth(),
        json={"insurance_warned": True},
    )
    assert r.status_code == 200
    assert r.json()["insurance_warned"] is True


@pytest.mark.asyncio
async def test_trojan_compose(client, store):
    store.write(
        "копилка_жалоб.md",
        {
            "trust_tier": "unverified",
            "date": "2026-07-19",
            "entries": [
                {
                    "id": "c1",
                    "text": "Пульс 85",
                    "severity": 6,
                    "resolved": False,
                    "specialty_hint": "Кардиолог",
                }
            ],
        },
        "",
    )

    r = await client.post(
        "/api/trojan/compose",
        headers=_auth(),
        json={
            "specialty": "Кардиология",
            "complaint_ids": ["c1"],
            "booster_ids": ["boost-cardio-1"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mix_ok"] is True
    assert "Кардиология" in body["script"]
    assert "Пульс 85" in body["script"]
