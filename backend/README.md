# SOUSCHEF Voice & Cooking Engine API

This backend integrates voice processing (Whisper STT, Rime TTS, NVIDIA NIM LLM) and the cooking session engine with real-time Spoonacular recipe integration.

Runtime recipes are fetched directly from Spoonacular API. The application does not ship with or fall back to an internal recipe catalogue (`data/recipes.json` has been removed).

## Quick Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Configure environment variables in .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Voice Synthesize Endpoint

`POST /api/voice/synthesize` sends short text to Rime and streams the resulting WAV bytes back to the caller.

```bash
curl --fail --request POST http://127.0.0.1:8000/api/voice/synthesize \
  --header 'Content-Type: application/json' \
  --data '{"text":"Add two teaspoons of salt."}' \
  --output souschef.wav
```

## Running Tests

```bash
pytest
```

