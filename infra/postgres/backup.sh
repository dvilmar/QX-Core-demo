#!/bin/sh
set -eu
DIR="${BACKUP_DIR:-/backups}"
KEEP="${BACKUP_KEEP:-14}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
mkdir -p "$DIR"
while true; do
    STAMP=$(date -u +%Y%m%dT%H%M%SZ)
    TMP="$DIR/qx-$STAMP.dump.tmp"
    pg_dump -Fc > "$TMP" || { rm -f "$TMP"; exit 1; }
    mv "$TMP" "$DIR/qx-$STAMP.dump"
    ls -1t "$DIR"/qx-*.dump | tail -n +$((KEEP + 1)) | xargs -r rm --
    [ "${BACKUP_ONCE:-0}" = "1" ] && exit 0
    sleep "$INTERVAL"
done
