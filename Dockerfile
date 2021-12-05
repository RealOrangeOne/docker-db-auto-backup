FROM alpine:latest

RUN apk add --no-cache docker-cli bash

COPY ./db-auto-backup /etc/periodic/daily/db-auto-backup

CMD ["crond", "-f", "-l", "0"]
