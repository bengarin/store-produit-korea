#!/usr/bin/env bash
# Sauvegarde MySQL + médias de Ma Petite Corée (lecture seule sur les données : rien n'est modifié).
#
#   MYSQL_CNF=/etc/mapetitecoree/backup.cnf DB_NAME=mapetitecoree \
#   MEDIA_ROOT=/srv/mapetitecoree/media BACKUP_DIR=/var/backups/mapetitecoree ./backup.sh
#
# MYSQL_CNF : fichier d'options MySQL (chmod 600) contenant [client] user=… password=… host=… port=…
#             → le mot de passe n'apparaît jamais dans la ligne de commande ni dans les journaux.
# RETENTION_DAYS (facultatif) : supprime les SAUVEGARDES plus anciennes (jamais les données). Vide = rien supprimé.
# Résultat : BACKUP_DIR/AAAAMMJJ-HHMMSS/{db.sql.gz, media.tar.gz, SHA256SUMS}. Code de sortie ≠ 0 en cas d'échec.
set -euo pipefail
: "${MYSQL_CNF:?MYSQL_CNF manquant}" "${DB_NAME:?DB_NAME manquant}" "${MEDIA_ROOT:?MEDIA_ROOT manquant}" "${BACKUP_DIR:?BACKUP_DIR manquant}"
MYSQLDUMP=${MYSQLDUMP:-mysqldump}
umask 077
stamp=$(date -u +%Y%m%d-%H%M%S)
dir="$BACKUP_DIR/$stamp"
mkdir -p "$dir"

# --single-transaction : copie cohérente sans bloquer la boutique (InnoDB).
"$MYSQLDUMP" --defaults-extra-file="$MYSQL_CNF" --single-transaction --quick --triggers --hex-blob \
  --no-tablespaces --set-gtid-purged=OFF --default-character-set=utf8mb4 "$DB_NAME" | gzip -9 > "$dir/db.sql.gz"
gzip -t "$dir/db.sql.gz"
gunzip -c "$dir/db.sql.gz" | tail -n 1 | grep -q "Dump completed" || { echo "Sauvegarde MySQL incomplète" >&2; exit 1; }

if [ -d "$MEDIA_ROOT" ]; then
  tar -C "$(dirname "$MEDIA_ROOT")" -czf "$dir/media.tar.gz" "$(basename "$MEDIA_ROOT")"
else
  echo "Attention : dossier des médias introuvable ($MEDIA_ROOT)" >&2
fi
(cd "$dir" && sha256sum ./*.gz > SHA256SUMS)
echo "Sauvegarde OK : $dir ($(du -sh "$dir" | cut -f1))"

if [ -n "${RETENTION_DAYS:-}" ]; then
  find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20??????-??????' -mtime +"$RETENTION_DAYS" -print -exec rm -rf {} +
fi
