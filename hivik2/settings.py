import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-#uuzkn6=^^16hmq^^3csx$l)@q+3itn=wmxtt4a@rnxt9iqfxi'
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
# DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ['true', '1']
ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    'got.apps.GotConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'storages',
    'widget_tweaks',
    'rest_framework',
    'corsheaders',
    'debug_toolbar',
    'overtime.apps.OvertimeConfig',
    'preoperacionales.apps.PreoperacionalesConfig',
    'outbound.apps.OutboundConfig',
    'megger_app.apps.MeggerAppConfig',
    'taggit',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'got.middleware.RequestTimingMiddleware',
]

CORS_ORIGIN_ALLOW_ALL = True 

ROOT_URLCONF = 'hivik2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'got.context_processors.unapproved_requests_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'hivik2.wsgi.application'

load_dotenv()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "dbmaster",
        "USER": "dbmasteruser",
        "PASSWORD": os.getenv('DATABASE_PASSWORD'),
        "HOST": "ls-d8139c3d44c02d059a5520fc27dfb9afd932ec3c.c1488e8iswlk.us-east-1.rds.amazonaws.com",
        "DATABASE_PORT": "5432",
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator'
        ),
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'es-co'

# TIME_ZONE = 'UTC'
TIME_ZONE = 'America/Bogota'

USE_I18N = True
USE_L10N = True
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

LOGIN_REDIRECT_URL = '/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')
STATIC_TMP = os.path.join(BASE_DIR, 'static')

os.makedirs(STATIC_TMP, exist_ok=True)

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = 'analistamto@serport.co'
EMAIL_HOST_PASSWORD = 'jkgg ryux ners zrsa'
EMAIL_USE_SSL = False

AWS_ACCESS_KEY_ID = 'AKIAYS2NTXT562AU74PQ'
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',  # Puedes cambiar a 'simple' si prefieres
        },
    },
    'loggers': {
        # Configuración para tu aplicación
        'got': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Asegúrate de que el nivel sea DEBUG
            'propagate': False,
        },
        # Configuración para Django
        'django': {
            'handlers': ['console'],
            'level': 'INFO',  # Puedes cambiar a DEBUG si deseas más detalles
            'propagate': False,
        },
    },
}

MY_SITE_DOMAIN = 'got.serport.co'
MY_SITE_NAME = 'Got Serport'

# * PAGINATION 

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

