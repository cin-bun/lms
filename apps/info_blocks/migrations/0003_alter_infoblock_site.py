# Generated by Django 3.2.18 on 2025-02-03 18:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('info_blocks', '0002_auto_20200902_0811'),
    ]

    operations = [
        migrations.AlterField(
            model_name='infoblock',
            name='site',
            field=models.ForeignKey(default=3, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='sites.site', verbose_name='Site'),
        ),
    ]
