FROM python:3.12-slim

COPY src /bot

RUN apt update && apt install -y ffmpeg && apt clean && rm -rf /var/lib/apt/lists/* && \
    python -m pip install -r /bot/requirements.txt

CMD ["python", "/bot/main.py"]