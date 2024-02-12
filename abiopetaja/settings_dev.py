from abiopetaja.settings_common import *  # noqa: F403

SECRET_KEY = "django-insecure-4k9w_ulf47yv^#^d(one)im0x7)sc7k9d_rcm3o+b00r1ri*fx"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "192.168.0.15", "192.168.0.10"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
