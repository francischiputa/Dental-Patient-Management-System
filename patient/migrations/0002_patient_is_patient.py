# Generated by Django 5.1.6 on 2025-06-24 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patient", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="is_patient",
            field=models.BooleanField(default=True),
        ),
    ]
