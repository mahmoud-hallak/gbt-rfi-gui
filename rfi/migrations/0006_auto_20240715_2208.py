# Generated by Django 3.2.25 on 2024-07-15 22:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rfi', '0005_auto_20240715_1853'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='frequency',
            name='view_level_0',
        ),
        migrations.RemoveField(
            model_name='frequency',
            name='view_level_1',
        ),
        migrations.RemoveField(
            model_name='frequency',
            name='view_level_2',
        ),
    ]
