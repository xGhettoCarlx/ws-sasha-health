# Project5 — AI Agent Rules

## Стек

- **Python 3.12+**, **FastAPI**, **aiogram**
- **xAI API** для AI функций (не OpenAI, не Anthropic)
- **PostgreSQL** через Supabase

## Docker

- Всегда multi-stage (builder + runtime)
- Базовый образ: `python:3.12-slim`
- Non-root user: `appuser` (UID 1000)
- HEALTHCHECK обязателен
- Volume: `./data:/app/data` для runtime данных
- Port: 8000

## Переменные окружения

- `BOT_TOKEN` — Telegram Bot токен
- `XAI_API_KEY` — xAI API ключ
- `DATA_DIR` — путь к данным (по умолчанию `/app/data`)

## Код-стайл

- Async endpoints везде (FastAPI)
- Pydantic models для валидации запросов/ответов
- Аннотации типов обязательны
- `ruff` для форматирования и линтинга

## Тесты

- `pytest` с `asyncio_mode="auto"`
- `pytest-cov` для coverage
- Smoke test: GET /health → `{"status":"healthy"}`

## Git

- Секреты никогда не коммитить
- `.env`, `__pycache__/`, `data/`, `*.pyc`, `.DS_Store` — в .gitignore
