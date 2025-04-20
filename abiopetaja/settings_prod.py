import os

from abiopetaja.settings_common import *  # noqa: F403
from abiopetaja.settings_common import BASE_DIR

DEBUG = False

with open("/home/abiopetaja/DJANGO_SECRET_KEY.txt") as f:
    SECRET_KEY = f.read().strip()

ALLOWED_HOSTS = ["*"]

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
