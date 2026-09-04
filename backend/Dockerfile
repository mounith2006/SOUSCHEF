FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime dependencies:
# - ffmpeg: lets Whisper process browser formats such as WebM/Opus
# - libsndfile1: audio file support
# - libportaudio2: supports sounddevice for local/manual microphone testing
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app ./app
COPY .env.example ./.env.example

# Download the Whisper model during the image build so the
# first API request does not have to download it.
RUN python -c "import whisper; whisper.load_model('small')"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]