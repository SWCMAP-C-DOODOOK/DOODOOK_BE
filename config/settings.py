import os
from pathlib import Path
from typing import Optional

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- simple .env loader (no external deps) ---
def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        # keep existing env if already set
        if key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "t", "yes", "y"}


_load_env_file(BASE_DIR / ".env")

try:
    import django_filters  # noqa: F401
except ImportError:
    _HAS_DJANGO_FILTERS = False
else:
    _HAS_DJANGO_FILTERS = True

RECEIPT_MAX_MB = float(os.environ.get("RECEIPT_MAX_MB", "10"))
RECEIPT_ALLOWED_EXTS = [
    ext.strip().lower()
    for ext in os.environ.get("RECEIPT_ALLOWED_EXTS", "jpg,jpeg,png,pdf").split(",")
    if ext.strip()
]
if not RECEIPT_ALLOWED_EXTS:
    RECEIPT_ALLOWED_EXTS = ["jpg", "jpeg", "png", "pdf"]

KAKAO_LOGIN_REDIRECT_URL = os.environ.get("KAKAO_LOGIN_REDIRECT_URL", "")
CLOVA_OCR_API_URL = os.environ.get("CLOVA_OCR_API_URL", "")
CLOVA_OCR_SECRET = os.environ.get("CLOVA_OCR_SECRET", "")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-for-prod")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _get_bool("DEBUG", True)

ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h] or []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "storages",
    # local apps
    "apps.budget",
    "apps.openbanking",
    "apps.ocr",
    "apps.ledger",
    "apps.dues",
    "apps.common",
    "apps.users",
]

if not _HAS_DJANGO_FILTERS:
    INSTALLED_APPS.remove("django_filters")

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# Defaults to SQLite for local dev; set DB_ENGINE=postgresql with envs to use Postgres
DB_ENGINE = os.environ.get("DB_ENGINE", "sqlite").lower()

if DB_ENGINE in {"postgres", "postgresql", "psql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", ""),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "ko-kr")

TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Seoul")

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# DRF
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}


# S3 storage (django-storages)
USE_S3 = _get_bool("USE_S3", False)
if USE_S3:
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
    AWS_S3_REGION_NAME: Optional[str] = os.environ.get("AWS_S3_REGION_NAME") or None
    AWS_S3_SIGNATURE_VERSION = os.environ.get("AWS_S3_SIGNATURE_VERSION", "s3v4")
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False

    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"


# Security recommended settings via env (no hardcoding)
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if _get_bool("USE_X_FORWARDED_PROTO", False)
    else None
)


# OpenBanking configuration
OPENBANKING_BASE_URL = os.environ.get(
    "OPENBANKING_BASE_URL", "https://testapi.openbanking.or.kr"
)
OPENBANKING_ACCESS_TOKEN = os.environ.get("OPENBANKING_ACCESS_TOKEN", "")
OPENBANKING_TIMEOUT = int(os.environ.get("OPENBANKING_TIMEOUT", "6"))
OPENBANKING_RETRIES = int(os.environ.get("OPENBANKING_RETRIES", "2"))
OPENBANKING_RL = int(os.environ.get("OPENBANKING_RL", "5"))
OPENBANKING_CLIENT_ID = os.environ.get("OPENBANKING_CLIENT_ID", "")
OPENBANKING_CLIENT_SECRET = os.environ.get("OPENBANKING_CLIENT_SECRET", "")
OPENBANKING_CLIENT_USE_CODE = os.environ.get("OPENBANKING_CLIENT_USE_CODE", "")
OPENBANKING_REDIRECT_URI = os.environ.get("OPENBANKING_REDIRECT_URI", "")
OPENBANKING_SCOPE = os.environ.get("OPENBANKING_SCOPE", "oob")
OPENBANKING_TOKEN_PATH = os.environ.get("OPENBANKING_TOKEN_PATH", "/oauth/2.0/token")
OPENBANKING_SANDBOX = _get_bool("OPENBANKING_SANDBOX", True)
# TODO: add structured logging / retry policy for OpenBanking client


# CORS settings
CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    o for o in os.environ.get("CORS_ALLOWED_ORIGIN_REGEXES", "").split(",") if o
]
CORS_ALLOW_CREDENTIALS = True


# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", os.environ.get("DJANGO_LOG_LEVEL", "INFO"))
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": True,
        },
    },
}
