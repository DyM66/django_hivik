import os
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY no está definida en las variables de entorno")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
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
    'preoperacionales.apps.PreoperacionalesConfig',
    'outbound.apps.OutboundConfig',
    'meg.apps.MegConfig',
    'inv.apps.InvConfig',
    'dth.apps.DthConfig', 
    'mto.apps.MtoConfig', 
    'ope.apps.OpeConfig', 
    'cont.apps.ContConfig', 
    'tic.apps.TicConfig', 
    'ntf.apps.NtfConfig', 
    'pwa',
    'storages',
    'widget_tweaks',
    'rest_framework',
    'corsheaders',
    'debug_toolbar',
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
                'tic.context_processors.ticket_form_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'hivik2.wsgi.application'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv('DATABASE_NAME'),
        "USER": os.getenv('DATABASE_USER'),
        "PASSWORD": os.getenv('DATABASE_PASSWORD'),
        "HOST": os.getenv('DATABASE_HOST'),
        "DATABASE_PORT": "5432",
    }
}

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

USE_I18N = True
USE_L10N = True
USE_TZ = False

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = '/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')
STATIC_TMP = os.path.join(BASE_DIR, 'static')

os.makedirs(STATIC_TMP, exist_ok=True)

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587 
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_USE_SSL = False

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
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
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Configuración para tu aplicación
        'got': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Configuración para Django
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

MY_SITE_DOMAIN = 'got.serport.co'
MY_SITE_NAME = 'Got Serport'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

DECIMAL_SEPARATOR = '.'
ASGI_APPLICATION = "hivik2.asgi.application"

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'

PROJECT_LOGO_URL = "https://hivik.s3.us-east-2.amazonaws.com/static/Outlook-fdeyoovu.png"


# Asumiendo que BASE_DIR está definido como la raíz del proyecto:
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static', 'js', 'service_worker.js')
# PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'service_worker.js')

# PWA settings
PWA_APP_NAME = 'GOT'
PWA_APP_SHORT_NAME = 'GOT'
PWA_APP_DESCRIPTION = 'Gestión de Operaciones Serport'
PWA_APP_THEME_COLOR = '#191645'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY = 'standalone'  # Obligatorio para app independiente
PWA_APP_SCOPE = '/'
PWA_APP_START_URL = '/'
# PWA_APP_ICONS = [
#     {
#         'src': 'https://hivik.s3.us-east-2.amazonaws.com/static/Outlook-fdeyoovu.png',
#         'sizes': '192x192',
#         'type': 'image/png'
#     },
#     {
#         'src': 'https://hivik.s3.us-east-2.amazonaws.com/static/Outlook-fdeyoovu.png',
#         'sizes': '512x512',
#         'type': 'image/png'
#     }
# ]
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'es-CO'
