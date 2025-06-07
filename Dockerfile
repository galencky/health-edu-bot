# ── Base image ────────────────────────────────────────────────────────
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# ── System deps ──────────────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# ── Non-root user ────────────────────────────────────────────────────
RUN useradd --create-home mededbot

# ── Working dir (matches your host folder name) ──────────────────────
WORKDIR /docker/mededbot-v4/app
USER mededbot

# ── Python deps ──────────────────────────────────────────────────────
COPY --chown=mededbot:mededbot requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir google-genai \
 && pip install --no-cache-dir -r requirements.txt

# ── App code ─────────────────────────────────────────────────────────
COPY --chown=mededbot:mededbot . .

# ── Writable dirs for audio files ────────────────────────────────────
RUN mkdir -p tts_audio voicemail

# ── Expose & launch on 10001 ─────────────────────────────────────────
EXPOSE 10001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10001"]
