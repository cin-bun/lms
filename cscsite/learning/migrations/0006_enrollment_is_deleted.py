# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-06-29 13:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_auto_20170614_1134'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='Student is left the course'),
        ),
    ]
