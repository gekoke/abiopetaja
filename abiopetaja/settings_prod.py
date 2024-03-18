from abiopetaja.settings_common import *  # noqa: F403

DEBUG = False

with open("/etc/DJANGO_SECRET_KEY.txt") as f:
    SECRET_KEY = f.read().strip()

ALLOWED_HOSTS = ["*"]

STATIC_ROOT = "/static"
STATIC_URL = "/"
MEDIA_URL = "/media/"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/db.sqlite3",
    }
}
