# Быстрый старт — Sasha Health

## Первый запуск

```bash
cd Projects/Project5

# 1. Установить зависимости
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Настроить переменные
cp .env.example .env
# Заполнить BOT_TOKEN и XAI_API_KEY из GeneralLibrary/secrets/active/projects/Project5/

# 3. Запустить сервер
uvicorn app.main:app --reload --port 8000

# 4. Проверить health
curl http://localhost:8000/health
```

## Docker

```bash
docker compose up --build -d
docker compose logs -f
```

## Тестирование

```bash
pytest -v
pytest --cov=app --cov-report=term-missing
```

## Ссылки

- Secrets: `GeneralLibrary/secrets/active/projects/Project5/`
- GeneralLibrary rules: `GeneralLibrary/rules/`
- WorkStation v2.1: `GeneralLibrary/templates/project-structure.md`
