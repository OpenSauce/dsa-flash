#!/bin/sh
set -e

TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
FILENAME="dsa-flash-${TIMESTAMP}.sql.gz"
LOCAL_PATH="/backups/${FILENAME}"

echo "[backup] Starting pg_dump at $(date)"
TEMP_SQL=$(mktemp "/backups/dsa-flash-${TIMESTAMP}.XXXXXX.sql")
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
  -h "${POSTGRES_HOST:-db}" \
  -U "${POSTGRES_USER:-user}" \
  -d "${POSTGRES_DB:-flashcards}" \
  --no-owner --no-acl \
  > "${TEMP_SQL}"
gzip -c "${TEMP_SQL}" > "${LOCAL_PATH}"
rm -f "${TEMP_SQL}"

SIZE=$(du -h "${LOCAL_PATH}" | cut -f1)
echo "[backup] Dump complete: ${FILENAME} (${SIZE})"

echo "[backup] Uploading to s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILENAME}"
aws s3 cp "${LOCAL_PATH}" "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILENAME}"

echo "[backup] Cleaning up S3 backups older than ${RETENTION_DAYS:-7} days"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
NOW_EPOCH=$(date +%s)
CUTOFF_EPOCH=$((NOW_EPOCH - RETENTION_DAYS * 86400))
aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}" | while read -r line; do
  FILE_DATE=$(echo "$line" | awk '{print $1}')
  FILE_NAME=$(echo "$line" | awk '{print $4}')
  if [ -z "$FILE_NAME" ]; then
    continue
  fi
  case "$FILE_NAME" in
    dsa-flash-*.sql.gz) ;;
    *) continue ;;
  esac
  FILE_EPOCH=$(date -d "$FILE_DATE" +%s 2>/dev/null || echo "")
  if [ -n "$FILE_EPOCH" ] && [ "$FILE_EPOCH" -lt "$CUTOFF_EPOCH" ]; then
    echo "[backup] Deleting old backup: ${FILE_NAME}"
    aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILE_NAME}"
  fi
done

rm -f "${LOCAL_PATH}"
echo "[backup] Done at $(date)"
