# Generated by Django 2.1.1 on 2018-10-19 13:39

from django.conf import settings
import django.contrib.auth.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import jsonfield.fields
import learning.permissions
import model_utils.fields
import sorl.thumbnail.fields
import users.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('learning', '0001_initial'),
        ('core', '0002_auto_20180730_1437'),
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSCUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female')], max_length=1, verbose_name='Gender')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('patronymic', models.CharField(blank=True, max_length=100, verbose_name='CSCUser|patronymic')),
                ('photo', sorl.thumbnail.fields.ImageField(blank=True, upload_to='photos/', verbose_name='CSCUser|photo')),
                ('cropbox_data', jsonfield.fields.JSONField(blank=True, null=True)),
                ('note', models.TextField(blank=True, help_text='LaTeX+Markdown is enabled', verbose_name='CSCUser|note')),
                ('enrollment_year', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1990)], verbose_name='CSCUser|enrollment year')),
                ('graduation_year', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1990)], verbose_name='CSCUser|graduation year')),
                ('curriculum_year', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(2000)], verbose_name='CSCUser|Curriculum year')),
                ('yandex_id', models.CharField(blank=True, max_length=80, validators=[django.core.validators.RegexValidator(message='Only the part before "@yandex.ru" is expected', regex='^[^@]*$')], verbose_name='Yandex ID')),
                ('github_id', models.CharField(blank=True, max_length=80, validators=[django.core.validators.RegexValidator(regex='^[a-zA-Z0-9](-?[a-zA-Z0-9])*$')], verbose_name='Github ID')),
                ('stepic_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='stepik.org ID')),
                ('csc_review', models.TextField(blank=True, help_text='LaTeX+Markdown is enabled', verbose_name='CSC review')),
                ('private_contacts', models.TextField(blank=True, help_text='доступны LaTeX и Markdown; показывается только залогиненным пользователям', verbose_name='Contact information')),
                ('university', models.CharField(blank=True, max_length=255, verbose_name='University')),
                ('phone', models.CharField(blank=True, max_length=40, verbose_name='Phone')),
                ('uni_year_at_enrollment', models.CharField(blank=True, choices=[('1', '1 course bachelor, speciality'), ('2', '2 course bachelor, speciality'), ('3', '3 course bachelor, speciality'), ('4', '4 course bachelor, speciality'), ('5', 'last course speciality'), ('6', '1 course magistracy'), ('7', '2 course magistracy'), ('8', 'postgraduate'), ('9', 'graduate')], help_text='at enrollment', max_length=2, null=True, verbose_name='StudentInfo|University year')),
                ('comment', models.TextField(blank=True, help_text='How to style text read <a href="/commenting-the-right-way/" target="_blank">here</a>.', verbose_name='Comment')),
                ('comment_changed_at', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='comment', verbose_name='Comment changed')),
                ('status', models.CharField(blank=True, choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')], help_text='Status|HelpText', max_length=15, verbose_name='Status')),
                ('workplace', models.CharField(blank=True, max_length=200, verbose_name='Workplace')),
                ('index_redirect', models.CharField(blank=True, choices=[('projects', 'Проекты'), ('admission', 'Набор'), ('learning', 'Обучение'), ('teaching', 'Преподавание'), ('staff', 'Курирование')], max_length=200, verbose_name='Index Redirect Option')),
                ('areas_of_study', models.ManyToManyField(blank=True, to='learning.AreaOfStudy', verbose_name='StudentInfo|Areas of study')),
                ('city', models.ForeignKey(blank=True, help_text='CSCUser|city', null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.City', verbose_name='Default city')),
                ('comment_last_author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cscuser_commented', to=settings.AUTH_USER_MODEL, verbose_name='Author of last edit')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
            ],
            options={
                'verbose_name': 'CSCUser|user',
                'verbose_name_plural': 'CSCUser|users',
                'ordering': ['last_name', 'first_name'],
            },
            bases=(learning.permissions.LearningPermissionsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='CSCUserReference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('signature', models.CharField(max_length=255, verbose_name='Reference|signature')),
                ('note', models.TextField(blank=True, verbose_name='Reference|note')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'verbose_name': 'User reference record',
                'verbose_name_plural': 'User reference records',
                'ordering': ['signature'],
            },
        ),
        migrations.CreateModel(
            name='CSCUserStatusLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(default=django.utils.timezone.now, verbose_name='created')),
                ('status', models.CharField(choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')], max_length=15, verbose_name='Status')),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='learning.Semester', verbose_name='Semester')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'ordering': ['-pk'],
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
            name='SHADCourseRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(max_length=255, verbose_name='Course|name')),
                ('teachers', models.CharField(max_length=255, verbose_name='Teachers')),
                ('grade', model_utils.fields.StatusField(choices=[('not_graded', 'Not graded'), ('unsatisfactory', 'Enrollment|Unsatisfactory'), ('pass', 'Enrollment|Pass'), ('good', 'Good'), ('excellent', 'Excellent')], default='not_graded', max_length=100, no_check_for_status=True, verbose_name='Enrollment|grade')),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='learning.Semester', verbose_name='Semester')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Student')),
            ],
            options={
                'verbose_name': 'SHAD course record',
                'verbose_name_plural': 'SHAD course records',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='cscuser',
            name='status_last_change',
            field=users.models.MonitorStatusField(blank=True, editable=False, logging_model=users.models.UserStatusLog, monitored='status', null=True, on_delete=django.db.models.deletion.CASCADE, to='users.CSCUserStatusLog', verbose_name='Status changed'),
        ),
        migrations.AddField(
            model_name='cscuser',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions'),
        ),
    ]
