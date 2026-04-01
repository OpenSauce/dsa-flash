FROM alpine:3.20

RUN apk add --no-cache postgresql16-client aws-cli

WORKDIR /app
COPY backup.sh restore.sh entrypoint.sh ./
RUN chmod +x backup.sh restore.sh entrypoint.sh

RUN mkdir -p /backups

ENTRYPOINT ["/app/entrypoint.sh"]
