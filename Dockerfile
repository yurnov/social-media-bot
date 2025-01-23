FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/ovchynnikov/load-bot-linux" \
        org.opencontainers.image.licenses="MIT" \
        org.opencontainers.image.title="Instagram bot" \
        org.opencontainers.image.description="Instagram bot for downloading images and videos"

RUN --mount=type=bind,target=/tmp/requirements.txt,source=src/requirements.txt \
    apt-get update && apt-get install --no-install-recommends -y ffmpeg && \
    apt-cache clean && rm -rf /var/lib/apt/lists/* && \
    python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY src /bot

WORKDIR /bot

CMD ["python", "main.py"]