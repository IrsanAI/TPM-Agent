FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl git tmux procps && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && python -m pip install --no-cache-dir -r /app/requirements.txt
COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/tpm_cli.py", "env"]
