# app/signals.py  –  default templates + topic helpers  (May 2025)
import logging
from typing import List, Tuple

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from app.models import Template
from app.topics import ALLOWED_TOPICS, DEFAULT_TRANSLATIONS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default template topics: one template per allowed topic
# ---------------------------------------------------------------------------
DEFAULT_TEMPLATE_TOPICS: List[Tuple[str, str]] = [
    (code, DEFAULT_TRANSLATIONS.get(code, _(code.replace("_", " ").title())))
    for code in ALLOWED_TOPICS
]

# ---------------------------------------------------------------------------
# Signal: create default templates for each new user
# ---------------------------------------------------------------------------
@receiver(post_save, sender=User)
def add_default_templates(sender, instance: User, created: bool, **kwargs):
    """For each allowed topic, create a template with 3 problems of each difficulty."""
    if not created:
        return

    user = instance
    for topic_code, topic_label in DEFAULT_TEMPLATE_TOPICS:
        # create the template
        template = Template.objects.create(
            name=topic_label,
            title=topic_label,
            author=user,
        )
        # add 3 problems of each difficulty in this topic
        for difficulty in ("A", "B", "C"):
            template.add_problem(
                topic=topic_code,
                difficulty=difficulty,
                count=3,
            )
        logger.info(
            "Created template '%s' for topic %s: 9 problems (3A+3B+3C)",
            topic_label,
            topic_code,
        )
