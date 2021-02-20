# Generated by Django 3.1.7 on 2021-02-20 17:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_user_calendar_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentprofile',
            name='level_of_education_on_admission',
            field=models.CharField(blank=True, choices=[('1', '1 course bachelor, speciality'), ('2', '2 course bachelor, speciality'), ('3', '3 course bachelor, speciality'), ('4', '4 course bachelor, speciality'), ('5', '5 course speciality'), ('6', '6 course speciality'), ('6', '1 course magistracy'), ('7', '2 course magistracy'), ('8', 'postgraduate'), ('9', 'graduate'), ('other', 'Other')], max_length=12, null=True, verbose_name='StudentInfo|University year'),
        ),
    ]
