"""Crée les 5 groupes de rôles. Les permissions fines seront ajoutées avec chaque module."""

from django.db import migrations

ROLES = ["owner", "admin", "order_manager", "content_editor", "analyst"]


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLES:
        Group.objects.get_or_create(name=name)


def remove_roles(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(create_roles, remove_roles)]
