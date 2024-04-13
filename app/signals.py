import logging

from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.utils.translation import gettext as _

from app.models import ProblemKind, Template

logger = logging.getLogger(__name__)


@receiver(user_signed_up)
def add_default_templates(user: User, **kwargs):
    template = Template()
    template.name = _("Inequalities")
    template.author = user
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
    template.save()

    template.add_problem(ProblemKind.LINEAR_INEQUALITY, count=6)
    template.add_problem(ProblemKind.QUADRATIC_INEQUALITY, count=6)
