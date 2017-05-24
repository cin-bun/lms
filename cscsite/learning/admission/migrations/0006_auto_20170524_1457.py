# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-24 11:57
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0005_auto_20170425_1618'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='status',
            field=models.CharField(blank=True, choices=[('rejected_test', 'Rejected by test'), ('permit_to_exam', 'Permitted to the exam'), ('rejected_exam', 'Rejected by exam'), ('rejected_cheating', 'Cheating'), ('pending', 'Pending'), ('interview_phase', 'Can be interviewed'), ('interview_assigned', 'Interview assigned'), ('interview_completed', 'Interview completed'), ('rejected_interview', 'Rejected by interview'), ('accept', 'Accept'), ('accept_if', 'Accept with condition'), ('volunteer', 'Applicant|Volunteer'), ('they_refused', 'He or she refused')], max_length=20, null=True, verbose_name='Applicant|Status'),
        ),
        migrations.AlterField(
            model_name='interview',
            name='applicant',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='interview', to='admission.Applicant', verbose_name='Applicant'),
        ),
    ]
