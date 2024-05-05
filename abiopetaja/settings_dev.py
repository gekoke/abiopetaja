from abiopetaja.settings_common import *  # noqa: F403
from abiopetaja.settings_common import BASE_DIR

SECRET_KEY = "django-insecure-4k9w_ulf47yv^#^d(one)im0x7)sc7k9d_rcm3o+b00r1ri*fx"

MEDIA_ROOT = BASE_DIR / "media"

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
