FROM python:alpine

WORKDIR /usr/src/db-auto-backup

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN ln -s /usr/src/db-auto-backup/db-auto-backup.py /etc/periodic/daily/db-auto-backup
RUN ln -s /usr/src/db-auto-backup/db-auto-backup.py /usr/local/bin/db-auto-backup

COPY ./db-auto-backup.py .


CMD ["crond", "-f", "-l", "0"]
