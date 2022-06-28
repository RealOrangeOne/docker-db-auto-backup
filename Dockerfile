FROM alpine as alpine

RUN apk add --no-cache supercronic

FROM python:slim

ENV SCHEDULE "@daily"

# Supercronic dynamically links to libc.musl
RUN apt-get update && \
  apt-get install -y musl-dev && \
  ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1 && \
  apt-get autoclean && \
  rm -rf \
    /var/lib/apt/lists/* \
    /var/tmp/* \
    /tmp/*

COPY --from=alpine /usr/bin/supercronic /usr/bin/supercronic

WORKDIR /usr/src/db-auto-backup
RUN mkdir -p /var/backups

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./db-auto-backup.py .

# HACK: Define a cronfile without defining a cronfile
CMD supercronic <(echo "$SCHEDULE" python3 db-auto-backup.py)
