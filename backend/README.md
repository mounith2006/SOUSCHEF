# SousChef voice API

This first milestone is deliberately small: `POST /api/voice/synthesize` sends
short text to Rime and streams the resulting WAV bytes back to the caller. The
Rime key stays on the server; recipe logic, speech recognition, and UI are not
part of this step.

## Run it

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set RIME_API_KEY in .env
uvicorn app.main:app --reload
```

In a second terminal, save a real audio file:

```bash
curl --fail --request POST http://127.0.0.1:8000/api/voice/synthesize \
  --header 'Content-Type: application/json' \
  --data '{"text":"Add two teaspoons of salt."}' \
  --output souschef.wav
```

Play `souschef.wav` with any audio player. The response is intentionally a WAV
file, which browsers can play directly. Voice/model/language defaults live in
`.env.example` so a demo can be reproduced without hard-coding credentials.

## Verify without a Rime key

```bash
pytest
```
