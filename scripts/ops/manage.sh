#!/usr/bin/env bash
# Lance une commande Django avec les réglages de PRODUCTION (pour cron et l'exploitation).
#   ENV_FILE=/etc/mpc/production.env VENV=/srv/mpc/venv scripts/ops/manage.sh send_pending_emails
set -euo pipefail
: "${ENV_FILE:?ENV_FILE manquant (fichier des variables de production)}" "${VENV:?VENV manquant (environnement Python)}"
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
cd "$(dirname "$0")/../../backend"
export DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_ENV_FILE=none
exec "$VENV/bin/python" manage.py "$@"
