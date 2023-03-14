FROM python:3.11-alpine

ENV SCHEDULE "@daily"

RUN apk add --no-cache git

WORKDIR /usr/src/db-auto-backup
RUN mkdir -p /var/backups

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./db-auto-backup.py .

CMD ["python3", "./db-auto-backup.py"]
