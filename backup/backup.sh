#!/bin/sh
set -e

TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
FILENAME="dsa-flash-${TIMESTAMP}.sql.gz"
LOCAL_PATH="/backups/${FILENAME}"

echo "[backup] Starting pg_dump at $(date)"
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h "${POSTGRES_HOST:-db}" \
  -U "${POSTGRES_USER:-user}" \
  -d "${POSTGRES_DB:-flashcards}" \
  --no-owner --no-acl \
  | gzip > "${LOCAL_PATH}"

SIZE=$(du -h "${LOCAL_PATH}" | cut -f1)
echo "[backup] Dump complete: ${FILENAME} (${SIZE})"

echo "[backup] Uploading to s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILENAME}"
aws s3 cp "${LOCAL_PATH}" "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILENAME}"

echo "[backup] Cleaning up S3 backups older than ${RETENTION_DAYS:-7} days"
CUTOFF=$(date -d "-${RETENTION_DAYS:-7} days" +%Y-%m-%d 2>/dev/null \
  || date -v-${RETENTION_DAYS:-7}d +%Y-%m-%d)
aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}" | while read -r line; do
  FILE_DATE=$(echo "$line" | awk '{print $1}')
  FILE_NAME=$(echo "$line" | awk '{print $4}')
  if [ -n "$FILE_NAME" ] && [ "$FILE_DATE" \< "$CUTOFF" ]; then
    echo "[backup] Deleting old backup: ${FILE_NAME}"
    aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILE_NAME}"
  fi
done

rm -f "${LOCAL_PATH}"
echo "[backup] Done at $(date)"
