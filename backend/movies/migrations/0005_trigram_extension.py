from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("movies", "0004_alter_castcredit_character_name_alter_person_name"),
    ]

    operations = [
        TrigramExtension(),
    ]
