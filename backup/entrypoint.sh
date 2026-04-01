#!/bin/sh
set -e

INTERVAL=${BACKUP_INTERVAL_SECONDS:-86400}

echo "[backup] Starting backup service (interval: ${INTERVAL}s)"
echo "[backup] Bucket: s3://${S3_BUCKET}/${S3_PREFIX:-backups/}"

# Run first backup immediately on start
/app/backup.sh

while true; do
  echo "[backup] Next backup in ${INTERVAL}s"
  sleep "${INTERVAL}"
  /app/backup.sh
done
