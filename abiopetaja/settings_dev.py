from abiopetaja.settings_common import *  # noqa: F403
from abiopetaja.settings_common import BASE_DIR
import os
import dj_database_url
from dotenv import load_dotenv

SECRET_KEY = "django-insecure-4k9w_ulf47yv^#^d(one)im0x7)sc7k9d_rcm3o+b00r1ri*fx"

MEDIA_ROOT = BASE_DIR / "media"

DEBUG = True

ALLOWED_HOSTS = ["*"]
# Otherwise we get rate limited in CI
ACCOUNT_RATE_LIMITS = False
load_dotenv(BASE_DIR / ".env")
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL"),
        conn_max_age=600,           # keep connections around
        ssl_require=False           # set True in prod behind SSL
    )
}