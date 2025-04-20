# signals.py
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


def get_all_topics():
    problems_path = os.path.join(settings.BASE_DIR, "problems.json")
    try:
        with open(problems_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        topics = list(data.keys())
        logger.info("Found topics: %s", topics)
        return topics
    except Exception as e:
        logger.error("Error reading problems.json: %s", e)
        return []


@receiver(post_save, sender=User)
def add_default_templates(sender, instance: User, created: bool, **kwargs):
    if not created:
        return

    user = instance

    # Define topics from your database. Here’s an example using hard-coded values.
    topics = [
        ("ARVUHULGAD", _("Arvuhulgad")),
        ("AVALDISED", _("Avaldised")),
        ("EKSPONENT- ja LOGARITMFUNKTSIOON", _("Eksponent- ja logaritmfunktsioon")),
        ("FUNKTSIOONID JA ARVJADAD", _("Funktsioonid ja arvjadad")),
        ("TRIGONOMEETRILISED I JA II", _("Trigonomeetrilised I ja II")),
        ("VÕRRANDID JA VÕRRANDISÜSTEEMID", _("Võrrandid ja võrrandisüsteemid")),
        ("VÕRRATUSED JA VÕRRATUSESÜSTEEMID", _("Võrratused ja võrratusesüsteemid")),
        ("VEKTOR TASANDIL JA JOONE VÕRRAND", _("Vektor tasandil ja joone võrrand")),
        (
            "TRIGONOMEETRILISED FUNKTSIOONID. FUNKTSIOONI PIIRVÄÄRTUS JA TULETIS",
            _("Trigonomeetrilised funktsioonid, piirväärtus ja tulemised"),
        ),
        ("TULETISE RAKENDUSED", _("Tuletise rakendused")),
        ("INTEGRAAL ja PLANIMEETRIA", _("Integraal ja planimeetria")),
        ("SIRGE JA TASAND RUUMIS", _("Sirge ja tasand ruumis")),
        ("STEREOMEETRIA", _("Stereomeetria")),
        (
            "MATEMAATIKA RAKENDUSED, REAALSETE PROTSESSIDE UURIMINE",
            _("Matemaatika rakendused, reaalse protsessi uurimine"),
        ),
    ]

    # For each topic, create a template with default problems for each difficulty.
    for topic_code, topic_name in topics:
        template = Template()
        template.name = topic_name
        template.author = user
        template.title = topic_name
        template.save()

        # For example, add 3 easy, 3 medium, and 3 hard problems per template.
        template.add_problem(topic=topic_code, difficulty="A", count=3)
        template.add_problem(topic=topic_code, difficulty="B", count=3)
        template.add_problem(topic=topic_code, difficulty="C", count=3)

    if not settings.DEBUG:
        return

    add_test_templates(user)


def add_test_templates(user: User, **kwargs):
    topics = get_all_topics()
    selected_topic = topics[0] if topics else "ARVUHULGAD"
    template = Template.objects.create(name=_("Test Mall"), title=_("Test Mall"), author=user)
    template.add_problem(topic=selected_topic, difficulty="A", count=6)
    template.add_problem(topic=selected_topic, difficulty="B", count=6)
    template.add_problem(topic=selected_topic, difficulty="C", count=6)
    logger.info(
        "Created extra test template for user '%s' with topic '%s'", user.username, selected_topic
    )
