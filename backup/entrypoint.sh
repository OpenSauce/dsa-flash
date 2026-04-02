#!/bin/sh
set -e

INTERVAL=${BACKUP_INTERVAL_SECONDS:-86400}

for var in POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB S3_BUCKET; do
  eval val=\$$var
  if [ -z "$val" ]; then
    echo "[backup] ERROR: $var is not set. Exiting."
    exit 1
  fi
done

echo "[backup] Starting backup service (interval: ${INTERVAL}s)"
echo "[backup] Bucket: s3://${S3_BUCKET}/${S3_PREFIX:-backups/}"

# Wait for Postgres to become ready before the first backup
echo "[backup] Waiting for Postgres at ${POSTGRES_HOST:-db}:5432..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p 5432 -U "${POSTGRES_USER:-user}" >/dev/null 2>&1; do
  sleep 5
done
echo "[backup] Postgres is ready."

# Run first backup immediately on start
/app/backup.sh

while true; do
  echo "[backup] Next backup in ${INTERVAL}s"
  sleep "${INTERVAL}"
  /app/backup.sh
done
