"""
Project settings
"""
import sys
import django

import environ

from core.settings.base import *

sys.path.append(str(ROOT_DIR / "compsciclub_ru" / "apps"))

env = environ.Env()
environ.Env.read_env()  # reading .env file

SITE_ID = 2

DEBUG = MODELTRANSLATION_DEBUG = env.bool('DEBUG', default=False)

PROJECT_DIR = Path(__file__).parents[1]

FILE_UPLOAD_DIRECTORY_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_DIRECTORY_PERMISSIONS', default=0o755)
FILE_UPLOAD_PERMISSIONS = env.int('DJANGO_FILE_UPLOAD_PERMISSIONS', default=0o664)

# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": env.db_url(var="DATABASE_URL")
}

ROOT_URLCONF = 'compsciclub_ru.urls'
LMS_SUBDOMAIN = None
SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF
}
WSGI_APPLICATION = 'compsciclub_ru.wsgi.application'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'notifications.middleware.UnreadNotificationsCacheMiddleware',
    'core.middleware.CurrentBranchMiddleware',
    'core.middleware.RedirectMiddleware',
]

INSTALLED_APPS += [
    'international_schools.apps.Config',
    'compsciclub_ru.project_conf.ProjectConfig',  # should be the last one
]

REDIS_PASSWORD = env.str('REDIS_PASSWORD', default=None)
REDIS_HOST = env.str('REDIS_HOST', default='127.0.0.1')
RQ_QUEUES = {
    'default': {
        'HOST': REDIS_HOST,
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
    'high': {
        'HOST': REDIS_HOST,
        'PORT': 6379,
        'DB': 0,
        'PASSWORD': REDIS_PASSWORD,
    },
}


# https://sorl-thumbnail.readthedocs.io/en/latest/reference/settings.html
THUMBNAIL_DEBUG = DEBUG
THUMBNAIL_DUMMY = True
THUMBNAIL_PRESERVE_FORMAT = True
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
THUMBNAIL_REDIS_HOST = REDIS_HOST
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

LOCALE_PATHS = [
    str(PROJECT_DIR / "locale"),
] + LOCALE_PATHS

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [
            str(PROJECT_DIR / "templates"),
            str(SHARED_APPS_DIR / "templates"),
            django.__path__[0] + '/forms/templates',
        ],
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'compsciclub_ru.context_processors.get_branches',
                'core.context_processors.subdomain',
            ),
            'debug': DEBUG
        }
    },
]
FORM_RENDERER = 'django.forms.renderers.DjangoTemplates'

SECRET_KEY = env('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".compsciclub.ru"])

# Email settings
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compsciclub.ru'
EMAIL_HOST = env.str('DJANGO_EMAIL_HOST', default='smtp.yandex.ru')
EMAIL_HOST_PASSWORD = env.str('DJANGO_EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('DJANGO_EMAIL_PORT', default=465)
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

NEWRELIC_CONF = str(PROJECT_DIR / "newrelic.ini")
NEWRELIC_ENV = env.str('NEWRELIC_ENV', default='production')

HASHIDS_SALT = env.str('HASHIDS_SALT')

YANDEX_DISK_USERNAME = env.str('YANDEX_DISK_USERNAME')
YANDEX_DISK_PASSWORD = env.str('YANDEX_DISK_PASSWORD')

# Default keys are taken from https://developers.google.com/recaptcha/docs/faq
RECAPTCHA_PUBLIC_KEY = env.str('RECAPTCHA_PUBLIC_KEY', default="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")
RECAPTCHA_PRIVATE_KEY = env.str('RECAPTCHA_PRIVATE_KEY', default="6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")
RECAPTCHA_USE_SSL = True

ACCOUNT_ACTIVATION_DAYS = 2
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
REGISTRATION_FORM = 'compsciclub_ru.forms.RegistrationUniqueEmailAndUsernameForm'

ADMIN_REORDER = []

MIGRATION_MODULES = {
    "core": None,
    "courses": None,
    "htmlpages": None,
    "learning": None,
    "tasks": None,
    "gallery": None,
    "notifications": None,
    "library": None,
    "study_programs": None,
    "users": None,
}
