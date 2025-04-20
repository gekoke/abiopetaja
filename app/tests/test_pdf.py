import json
import logging
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext as _

from app.models import Template

logger = logging.getLogger(__name__)


def get_available_topics():
    """
    Reads the problems.json file (assumed to be in BASE_DIR) and returns a dictionary where:
      - the keys are the topic names (Estonian strings as they appear in your database), and
      - the values are dictionaries mapping each difficulty (e.g. "A", "B", "C") to a count.

    Example return value:
    {
      "ARVUHULGAD": {"A": 1, "B": 1, "C": 1},
      "AVALDISED": {"A": 1, "B": 2, "C": 1},
      ...
    }
    Here we use the length of the list for each difficulty as a suggestion.
    """
    problems_path = os.path.join(settings.BASE_DIR, "problems.json")
    try:
        with open(problems_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        topics = {}
        for topic, diff_dict in data.items():
            difficulties = {}
            for diff, problems in diff_dict.items():
                # Use at least 1 as default count.
                difficulties[diff] = max(1, len(problems))
            topics[topic] = difficulties
        logger.info("Available topics found: %s", topics)
        return topics
    except Exception as e:
        logger.error("Error reading problems.json: %s", e)
        return {}


@receiver(post_save, sender=User)
def add_default_templates(sender, instance: User, created: bool, **kwargs):
    if not created:
        return

    user = instance
    topics = get_available_topics()

    for topic, difficulties in topics.items():
        template = Template()
        template.name = _(topic)
        template.author = user
        template.title = _(topic)
        template.save()
        for diff, count in difficulties.items():
            # You can decide to use the suggested count from the JSON (count) or a fixed default.
            # Here we opt for a fixed default (3) for each difficulty.
            default_count = 3
            template.add_problem(topic=topic, difficulty=diff, count=default_count)
            logger.info(
                "Added %d problems for topic '%s', difficulty '%s'", default_count, topic, diff
            )

    # Optionally, if in DEBUG mode, add extra test templates.
    if settings.DEBUG:
        add_test_templates(user)


def add_test_templates(user: User, **kwargs):
    # Create an extra template for testing purposes.
    template = Template()
    template.name = _("Test Template")
    template.author = user
    template.title = _("Test Template")
    template.save()
    # For testing, choose one common topic, if it exists in your database. Here we use "ARVUHULGAD".
    template.add_problem(topic="ARVUHULGAD", difficulty="A", count=6)
    template.add_problem(topic="ARVUHULGAD", difficulty="B", count=6)
    template.add_problem(topic="ARVUHULGAD", difficulty="C", count=6)
    logger.info("Added test template for user: %s", user.username)
