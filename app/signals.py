import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from app.models import ProblemKind, Template

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def add_default_templates(sender, instance: User, created: bool, **kwargs):
    if not created:
        # Not a newly created user
        return

    user = instance

    template = Template()
    template.name = _("Inequalities")
    template.author = user
    template.title = _("Inequalities")
    template.save()

    template.add_problem(ProblemKind.LINEAR_INEQUALITY, count=3)
    template.add_problem(ProblemKind.QUADRATIC_INEQUALITY, count=3)

    if not settings.DEBUG:
        return

    add_test_templates(user)


def add_test_templates(user: User, **kwargs):
    template = Template()
    template.name = _("Lots of inequalities")
    template.author = user
    template.title = _("Lots of inequalities")
    template.save()

    template.add_problem(ProblemKind.LINEAR_INEQUALITY, count=6)
    template.add_problem(ProblemKind.QUADRATIC_INEQUALITY, count=6)
