FROM python:3.13-slim

ENV SCHEDULE="0 0 * * *"  PYTHONUNBUFFERED=1

RUN apt-get --yes update && apt-get --yes install git && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/db-auto-backup
RUN mkdir -p /var/backups

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./db-auto-backup.py .

CMD ["python3", "./db-auto-backup.py"]
