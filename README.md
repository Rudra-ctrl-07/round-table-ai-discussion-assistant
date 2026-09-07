# RT — Round Table

A personal assistant backend with a lightweight UI.

## Structure

- `backend/` — Python backend (FastAPI-style `app.py`, `round_table.py`, search + tool modules)
- `UI/` — UI mockup (`code.html`, design notes)
- `demo_insurance/` — demo data generator

## Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # then fill in your API keys
python app.py
```

## Tests

```bash
cd backend
python test_app.py
```