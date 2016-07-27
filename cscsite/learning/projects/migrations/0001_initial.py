# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-07-14 13:36
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import learning.projects.models
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # In learning migrations rename table
        ('learning', '0017_auto_20160714_1636'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    state_operations = [
        migrations.CreateModel(
            name='StudentProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, verbose_name='StudentProject|Name')),
                ('description', models.TextField(blank=True, help_text='LaTeX+<a href="http://en.wikipedia.org/wiki/Markdown">Markdown</a>+HTML is enabled', verbose_name='Description')),
                ('grade', model_utils.fields.StatusField(choices=[('not_graded', 'Not graded'), ('unsatisfactory', 'Enrollment|Unsatisfactory'), ('pass', 'Enrollment|Pass'), ('good', 'Good'), ('excellent', 'Excellent')], default='not_graded', max_length=100, no_check_for_status=True, verbose_name='Grade')),
                ('supervisor', models.CharField(help_text='Format: Last_name First_name Patronymic, Organization', max_length=255, verbose_name='StudentProject|Supervisor')),
                ('project_type', models.CharField(choices=[('practice', 'StudentProject|Practice'), ('research', 'StudentProject|Research')], max_length=10, verbose_name='StudentProject|Type')),
                ('presentation', models.FileField(blank=True, upload_to=learning.projects.models.project_presentation_files, verbose_name='Presentation')),
                ('is_external', models.BooleanField(default=False, verbose_name='External project')),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning.Semester', verbose_name='Semester')),
                ('students', models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Students')),
            ],
            options={
                'verbose_name_plural': 'Student projects',
                'verbose_name': 'Student project',
                'ordering': ['name'],
            },
        ),
    ]


    operations = [
        # By running only state operations, we are making Django think it has
        # applied this migration to the database. In reality, we renamed a
        # "learning_studentproject" table to "projects_studentproject" earlier.
        migrations.SeparateDatabaseAndState(state_operations=state_operations)
    ]
