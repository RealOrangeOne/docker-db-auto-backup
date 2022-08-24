FROM python:alpine

ENV SCHEDULE "@daily"

RUN apk add --no-cache supercronic tzdata

WORKDIR /usr/src/db-auto-backup
RUN mkdir -p /var/backups

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./db-auto-backup.py .

# HACK: Define a cronfile without defining a cronfile
CMD supercronic <(echo "$SCHEDULE" python3 db-auto-backup.py)
