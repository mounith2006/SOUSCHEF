# SOUSCHEF backend

Runtime recipes are fetched directly from Spoonacular. The application does not
ship with or fall back to an internal recipe catalogue.

Copy `.env.example` to `.env` and set `SPOONACULAR_API_KEY`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API. Provider responses
are normalized before a cooking session begins. Each session retains its recipe
snapshot, and tests use mocked HTTP responses without consuming provider quota.
