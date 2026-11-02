#!/usr/bin/env bash
# Restaure une sauvegarde dans une NOUVELLE base (jamais par-dessus une base existante) :
#
#   MYSQL_CNF=/etc/mapetitecoree/restore.cnf ./restore.sh /var/backups/mapetitecoree/20261102-030000 mpc_restauration [/srv/restauration/media]
#
# - vérifie les empreintes SHA256 ;
# - REFUSE si la base cible existe déjà (aucune donnée n'est jamais écrasée) ;
# - les médias sont extraits dans un dossier cible qui doit être vide ou absent.
# Ensuite : `python manage.py verify_backup --against mpc_restauration` compare la copie à la base d'origine,
# puis on bascule la configuration (DB_NAME) vers la base restaurée si c'est voulu.
set -euo pipefail
src=${1:?dossier de sauvegarde manquant}; target=${2:?nom de la base cible manquant}; media_target=${3:-}
: "${MYSQL_CNF:?MYSQL_CNF manquant}"
MYSQL=${MYSQL:-mysql}
[[ "$target" =~ ^[A-Za-z0-9_]{1,64}$ ]] || { echo "Nom de base invalide" >&2; exit 1; }
(cd "$src" && sha256sum -c SHA256SUMS)

exists=$("$MYSQL" --defaults-extra-file="$MYSQL_CNF" -N -e "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$target'")
if [ "$exists" != "0" ]; then
  echo "La base « $target » existe déjà : restauration refusée (rien n'est écrasé). Choisissez un autre nom." >&2
  exit 2
fi
"$MYSQL" --defaults-extra-file="$MYSQL_CNF" -e "CREATE DATABASE \`$target\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
gunzip -c "$src/db.sql.gz" | "$MYSQL" --defaults-extra-file="$MYSQL_CNF" --default-character-set=utf8mb4 "$target"
echo "Base restaurée : $target"

if [ -n "$media_target" ] && [ -f "$src/media.tar.gz" ]; then
  if [ -d "$media_target" ] && [ -n "$(ls -A "$media_target")" ]; then
    echo "Dossier médias cible non vide : extraction refusée ($media_target)" >&2; exit 3
  fi
  mkdir -p "$media_target"
  tar -C "$media_target" -xzf "$src/media.tar.gz"
  echo "Médias restaurés dans : $media_target"
fi
