# Generated by Django 3.2.25 on 2024-07-10 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rfi', '0003_file_path'),
    ]

    operations = [
        migrations.AddField(
            model_name='frequency',
            name='is_peak',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
