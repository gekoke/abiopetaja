import pytest
from django.test import Client
from django.urls import reverse

from app.models import UserFeedback
from app.tests.lib import create_user


@pytest.mark.django_db
def test_user_can_leave_feedback(client: Client):
    user = create_user(client)
    client.force_login(user)

    client.post(reverse("app:userfeedback-create"), {"content": "I love this app!"})

    feedback = UserFeedback.objects.filter(author=user).first()
    assert feedback is not None


@pytest.mark.django_db
def test_user_can_not_leave_blank_feedback(client: Client):
    user = create_user(client)
    client.force_login(user)

    client.post(reverse("app:userfeedback-create"), {"content": "   "})

    feedback = UserFeedback.objects.filter(author=user).first()
    assert feedback is None
