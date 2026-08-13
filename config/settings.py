"""
Django settings for LMS PRO.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-prod')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.core',
    'apps.tenants',
    'apps.accounts',
    'apps.catalog',
    'apps.payments',
    'apps.courses',
    'apps.learning_paths',
    'apps.assessments',
    'apps.virtual_classes',
    'apps.social',
    'apps.gamification',
    'apps.certificates',
    'apps.hr_analytics',
    'apps.kpi_pro',
    'apps.hr_agent',
    'apps.ai_engine',
    'apps.integrations',
    'apps.progression',
    'apps.content_security',
    'apps.notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenants.middleware.CurrentTenantMiddleware',
    'apps.content_security.middleware.AccessLogMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='lmspro'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static & media files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudflare R2 (S3-compatible) — used only for Lesson.video_file/document_file via
# apps.core.storage.r2_media_storage, so avatars/certificates/etc. stay on local disk.
USE_R2_STORAGE = config('USE_R2_STORAGE', default=False, cast=bool)
AWS_ACCESS_KEY_ID = config('R2_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('R2_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('R2_BUCKET_NAME', default='')
AWS_S3_ENDPOINT_URL = config('R2_ENDPOINT_URL', default='')
AWS_S3_REGION_NAME = 'auto'
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_ADDRESSING_STYLE = 'path'
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_EXPIRE = config('SIGNED_URL_TTL_SECONDS', default=600, cast=int)

# Max size for a lesson video/document uploaded directly to R2 (browser -> R2, bypasses
# nginx/Cloudflare entirely, so this is an app-level cap, not an infra one).
MAX_DIRECT_UPLOAD_MB = config('MAX_DIRECT_UPLOAD_MB', default=1024, cast=int)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.accounts.authentication.DeviceAwareJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.LmsPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'EXCEPTION_HANDLER': 'apps.core.exceptions.lmspro_exception_handler',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'apps.accounts.serializers.LmsTokenObtainPairSerializer',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'LMS PRO API',
    'DESCRIPTION': 'Plateforme de formation intelligente multi-tenant (B2C + B2B)',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://localhost:5173', cast=Csv())
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-device-id',
]

# --- LMS PRO specific settings ---

# Section 25/26: DRM & content protection
LMSPRO_CONTENT_SECURITY = {
    'SIGNED_URL_TTL_SECONDS': config('SIGNED_URL_TTL_SECONDS', default=600, cast=int),
    'MAX_CONCURRENT_DEVICES': config('MAX_CONCURRENT_DEVICES', default=2, cast=int),
    'DEFAULT_DOWNLOAD_ALLOWED': False,
    'WATERMARK_ENABLED': True,
}

# §25.2 — adaptive HLS streaming with AES-128 segment encryption. Requires the ffmpeg
# binary to be available on PATH (or set FFMPEG_BINARY to an absolute path).
FFMPEG_BINARY = config('FFMPEG_BINARY', default='ffmpeg')
HLS_SEGMENT_DURATION_SECONDS = config('HLS_SEGMENT_DURATION_SECONDS', default=6, cast=int)
HLS_PACKAGING_TIMEOUT_SECONDS = config('HLS_PACKAGING_TIMEOUT_SECONDS', default=1800, cast=int)

# Lot 9: AI engine — pluggable provider. 'dummy' works out of the box with no external API key.
LMSPRO_AI_PROVIDER = config('LMSPRO_AI_PROVIDER', default='dummy')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')

# Lot 2: Payment providers
LMSPRO_PAYMENT_PROVIDERS = {
    'STRIPE_SECRET_KEY': config('STRIPE_SECRET_KEY', default=''),
    'CINETPAY_API_KEY': config('CINETPAY_API_KEY', default=''),
    'CINETPAY_SITE_ID': config('CINETPAY_SITE_ID', default=''),
    'PAYPAL_CLIENT_ID': config('PAYPAL_CLIENT_ID', default=''),
    'PAYPAL_CLIENT_SECRET': config('PAYPAL_CLIENT_SECRET', default=''),
    'PAYPAL_MODE': config('PAYPAL_MODE', default='sandbox'),
}

FRONTEND_BASE_URL = config('FRONTEND_BASE_URL', default='http://localhost:5173')
BACKEND_BASE_URL = config('BACKEND_BASE_URL', default='http://localhost:8000')
CINETPAY_MOCK = config('CINETPAY_MOCK', default=False, cast=bool)

# Lot 6/17: multi-channel notifications
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@lmspro.local')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)

LMSPRO_NOTIFICATIONS = {
    'SMS_PROVIDER_URL': config('SMS_PROVIDER_URL', default=''),
    'SMS_PROVIDER_API_KEY': config('SMS_PROVIDER_API_KEY', default=''),
    'WHATSAPP_PROVIDER_URL': config('WHATSAPP_PROVIDER_URL', default=''),
    'WHATSAPP_PROVIDER_TOKEN': config('WHATSAPP_PROVIDER_TOKEN', default=''),
    'FCM_SERVER_KEY': config('FCM_SERVER_KEY', default=''),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
