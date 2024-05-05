from abiopetaja.settings_common import *  # noqa: F403

DEBUG = False

with open("/home/abiopetaja/DJANGO_SECRET_KEY.txt") as f:
    SECRET_KEY = f.read().strip()

ALLOWED_HOSTS = ["*"]

STATIC_ROOT = "/var/www/abiopetaja/static"
STATIC_URL = "/static/"

MEDIA_ROOT = "/var/www/abiopetaja/media"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/home/abiopetaja/db.sqlite3",
    }
}
