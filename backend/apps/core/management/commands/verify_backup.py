"""
Compare une base restaurée à la base en service (même serveur MySQL) — LECTURE SEULE :

    python manage.py verify_backup --against mpc_restauration

Pour chaque table : nombre de lignes et CHECKSUM TABLE. Code de sortie 1 si une différence est trouvée.
(Si la boutique a reçu des commandes depuis la sauvegarde, des différences sur ces tables sont normales.)
"""

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")


class Command(BaseCommand):
    help = "Compare une base restaurée à la base en service (lignes + empreintes par table)."

    def add_arguments(self, parser):
        parser.add_argument("--against", required=True)

    def handle(self, *args, against, **options):
        source = connection.settings_dict["NAME"]
        if not NAME.match(against) or not NAME.match(source):
            raise CommandError("Nom de base invalide.")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'",
                [source],
            )
            tables = sorted(r[0] for r in cur.fetchall())
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'",
                [against],
            )
            restored = {r[0] for r in cur.fetchall()}
            problems = sorted(set(tables) ^ restored)
            for t in problems:
                self.stdout.write(self.style.ERROR(f"Table présente d'un seul côté : {t}"))
            rows_total = 0
            for t in tables:
                if t not in restored or not NAME.match(t):
                    continue
                values = []
                for db in (source, against):
                    cur.execute(f"SELECT COUNT(*) FROM `{db}`.`{t}`")  # noqa: S608 - noms validés ci-dessus
                    count = cur.fetchone()[0]
                    cur.execute(f"CHECKSUM TABLE `{db}`.`{t}`")
                    values.append((count, cur.fetchone()[1]))
                rows_total += values[0][0]
                if values[0] != values[1]:
                    problems.append(t)
                    self.stdout.write(self.style.ERROR(f"{t} : en service {values[0]} ≠ restaurée {values[1]}"))
        if problems:
            raise CommandError(f"{len(problems)} différence(s).")
        self.stdout.write(
            self.style.SUCCESS(f"Identiques : {len(tables)} tables, {rows_total} lignes, empreintes égales.")
        )
