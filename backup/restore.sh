#!/bin/sh
set -e

if [ -z "$1" ]; then
  echo "Usage: restore.sh <filename>"
  echo ""
  echo "Available backups:"
  aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}" | grep '.sql.gz' | awk '{print "  " $4}'
  exit 1
fi

FILENAME="$1"
LOCAL_PATH="/backups/${FILENAME}"

echo "[restore] Downloading s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILENAME}"
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX:-backups/}${FILENAME}" "${LOCAL_PATH}"

echo "[restore] Restoring to ${POSTGRES_DB:-flashcards}..."
TEMP_SQL=$(mktemp "/backups/restore-XXXXXX")
gunzip -c "${LOCAL_PATH}" > "${TEMP_SQL}"
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  -h "${POSTGRES_HOST:-db}" \
  -U "${POSTGRES_USER:-user}" \
  -d "${POSTGRES_DB:-flashcards}" \
  --single-transaction -v ON_ERROR_STOP=1 \
  < "${TEMP_SQL}"
rm -f "${TEMP_SQL}"

rm -f "${LOCAL_PATH}"
echo "[restore] Done at $(date)"
