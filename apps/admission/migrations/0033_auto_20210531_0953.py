# Generated by Django 3.1.7 on 2021-05-31 09:53

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0032_auto_20210531_0758'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interviewinvitation',
            name='secret_code',
            field=models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Secret code'),
        ),
    ]
