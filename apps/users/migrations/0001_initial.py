# Generated by Django 2.2.4 on 2019-08-30 08:14

import core.timezone.models
from django.conf import settings
import django.contrib.auth.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

import model_utils.fields
import sorl.thumbnail.fields
import users.models
import users.thumbnails


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('courses', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('enrollment_year', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1990)], verbose_name='CSCUser|enrollment year')),
                ('curriculum_year', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(2000)], verbose_name='CSCUser|Curriculum year')),
                ('university', models.CharField(blank=True, max_length=255, verbose_name='University')),
                ('phone', models.CharField(blank=True, max_length=40, verbose_name='Phone')),
                ('uni_year_at_enrollment', models.CharField(blank=True, choices=[('1', '1 course bachelor, speciality'), ('2', '2 course bachelor, speciality'), ('3', '3 course bachelor, speciality'), ('4', '4 course bachelor, speciality'), ('5', 'last course speciality'), ('6', '1 course magistracy'), ('7', '2 course magistracy'), ('8', 'postgraduate'), ('9', 'graduate')], help_text='at enrollment', max_length=2, null=True, verbose_name='StudentInfo|University year')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('o', 'Other/Prefer Not to Say')], max_length=1, verbose_name='Gender')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('patronymic', models.CharField(blank=True, max_length=100, verbose_name='CSCUser|patronymic')),
                ('photo', sorl.thumbnail.fields.ImageField(blank=True, upload_to='photos/', verbose_name='CSCUser|photo')),
                ('cropbox_data', models.JSONField(blank=True, null=True)),
                ('bio', models.TextField(blank=True, help_text='LaTeX+Markdown is enabled', verbose_name='CSCUser|note')),
                ('yandex_login', models.CharField(blank=True, max_length=80, verbose_name='Yandex Login')),
                ('github_login', models.CharField(blank=True, max_length=80, validators=[django.core.validators.RegexValidator(regex='^[a-zA-Z0-9](-?[a-zA-Z0-9])*$')], verbose_name='Github Login')),
                ('stepic_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='stepik.org ID')),
                ('social_networks', models.TextField(blank=True, help_text='доступны LaTeX и Markdown; будут показаны только кураторам', null=True, verbose_name='Social Networks')),
                ('private_contacts', models.TextField(blank=True, help_text='доступны LaTeX и Markdown; показывается только залогиненным пользователям', verbose_name='Contact information')),
                ('status', models.CharField(blank=True, choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')], help_text='Status|HelpText', max_length=15, verbose_name='Status')),
                ('comment', models.TextField(blank=True, help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>.', verbose_name='Comment')),
                ('comment_changed_at', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='comment', verbose_name='Comment changed')),
                ('workplace', models.CharField(blank=True, max_length=200, verbose_name='Workplace')),
                ('index_redirect', models.CharField(blank=True, choices=[('projects', 'Проекты'), ('admission', 'Набор'), ('learning', 'Обучение'), ('teaching', 'Преподавание'), ('staff', 'Курирование')], max_length=200, verbose_name='Index Redirect Option')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.Branch', verbose_name='Branch')),
                ('comment_last_author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='user_commented', to=settings.AUTH_USER_MODEL, verbose_name='Author of last edit')),
            ],
            options={
                'verbose_name': 'CSCUser|user',
                'verbose_name_plural': 'CSCUser|users',
                'db_table': 'users_user',
            },
            bases=(core.timezone.models.TimezoneAwareModel,
                   users.models.LearningPermissionsMixin, users.thumbnails.UserThumbnailMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='name')),
            ],
            options={
                'verbose_name': 'group',
                'verbose_name_plural': 'groups',
            },
        ),
        migrations.CreateModel(
            name='UserStatusLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(default=django.utils.timezone.now, verbose_name='created')),
                ('status', models.CharField(choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')], max_length=15, verbose_name='Status')),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='courses.Semester', verbose_name='Semester')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='UserGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.PositiveSmallIntegerField(choices=[(1, 'Student'), (2, 'Teacher'), (3, 'Graduate'), (4, 'Volunteer'), (5, 'Curator'), (7, 'Interviewer [Admission]'), (8, 'Studying for a master degree'), (9, 'Project reviewer'), (10, 'Curator of projects'), (11, 'Invited User')], verbose_name='Role')),
                ('site', models.ForeignKey(db_index=False, default=users.models.get_current_site, on_delete=django.db.models.deletion.PROTECT, to='sites.Site', verbose_name='Site')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='groups', related_query_name='group', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Access Group',
                'verbose_name_plural': 'Access Groups',
                'db_table': 'users_user_groups',
            },
        ),
        migrations.CreateModel(
            name='SHADCourseRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('teachers', models.CharField(max_length=255, verbose_name='Teachers')),
                ('grade', models.CharField(choices=[('not_graded', 'Not graded'), ('unsatisfactory', 'SHADCourseGrade|Unsatisfactory'), ('pass', 'SHADCourseGrade|Pass'), ('good', 'Good'), ('excellent', 'Excellent')], default='not_graded', max_length=100, verbose_name='Enrollment|grade')),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='courses.Semester', verbose_name='Semester')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'verbose_name': 'SHAD course record',
                'verbose_name_plural': 'SHAD course records',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='OnlineCourseRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'verbose_name': 'Online course record',
                'verbose_name_plural': 'Online course records',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='EnrollmentCertificate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('signature', models.CharField(max_length=255, verbose_name='Reference|signature')),
                ('note', models.TextField(blank=True, verbose_name='Reference|note')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollment_certificates', to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'verbose_name': 'Student Reference',
                'verbose_name_plural': 'Student References',
                'ordering': ['signature'],
            },
        ),
        migrations.AddField(
            model_name='user',
            name='status_last_change',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.UserStatusLog', verbose_name='Status changed'),
        ),
        migrations.AddConstraint(
            model_name='usergroup',
            constraint=models.UniqueConstraint(fields=('user', 'role', 'site'), name='unique_user_role_site'),
        ),
    ]
