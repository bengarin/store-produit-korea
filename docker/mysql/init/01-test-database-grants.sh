#!/bin/bash
# Exécuté une seule fois, à la création du volume MySQL.
# Autorise l'utilisateur applicatif à créer/supprimer la base de TEST (test_<DB_NAME>)
# utilisée par pytest. Aucun autre droit global n'est accordé.
set -euo pipefail
mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
GRANT ALL PRIVILEGES ON \`test_${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
SQL
