#!/usr/bin/env bash
# Copie la DERNIÈRE sauvegarde (créée par backup.sh) HORS du serveur, avec rclone, puis vérifie la copie.
#
#   BACKUP_DIR=/srv/mpc/backups RCLONE_REMOTE=mpc-backup-chiffre:mapetitecoree ./offsite.sh
#
# RCLONE_REMOTE : destination rclone (ex. Backblaze B2, S3, Google Drive…) configurée UNE fois avec
#                 `rclone config` ; utiliser un remote de type « crypt » pour que les copies soient chiffrées.
#                 Les identifiants restent dans ~/.config/rclone/rclone.conf (chmod 600), jamais dans ce script.
# Ne supprime RIEN : ni sur le serveur, ni à distance (la durée de conservation se règle chez le fournisseur).
# Code de sortie ≠ 0 en cas d'échec (à surveiller : /var/log/mpc/backup.log).
set -euo pipefail
: "${BACKUP_DIR:?BACKUP_DIR manquant}" "${RCLONE_REMOTE:?RCLONE_REMOTE manquant}"
RCLONE=${RCLONE:-rclone}
command -v "$RCLONE" >/dev/null || { echo "rclone introuvable" >&2; exit 1; }

latest=$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20??????-??????' | sort | tail -n 1)
[ -n "$latest" ] || { echo "Aucune sauvegarde dans $BACKUP_DIR" >&2; exit 1; }
[ -f "$latest/SHA256SUMS" ] || { echo "Sauvegarde incomplète : $latest" >&2; exit 1; }
(cd "$latest" && sha256sum -c --quiet SHA256SUMS)   # n'envoie jamais une sauvegarde abîmée

name=$(basename "$latest")
"$RCLONE" copy "$latest" "$RCLONE_REMOTE/$name" --immutable
"$RCLONE" check "$latest" "$RCLONE_REMOTE/$name" --one-way   # relit la copie distante
echo "Copie externe OK : $name → $RCLONE_REMOTE/$name"
