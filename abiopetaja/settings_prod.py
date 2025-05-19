import os
from abiopetaja.settings_common import *  # noqa: F403
from abiopetaja.settings_common import BASE_DIR
import dj_database_url
from dotenv import load_dotenv
DEBUG = False

with open("/home/abiopetaja/DJANGO_SECRET_KEY.txt") as f:
    SECRET_KEY = f.read().strip()

ALLOWED_HOSTS = ["*"]

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

load_dotenv(BASE_DIR / ".env")
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL"),
        conn_max_age=600,           # keep connections around
        ssl_require=False           # set True in prod behind SSL
    )
}
