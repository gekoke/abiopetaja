import pytest
from django.test import Client
from django.urls import reverse

from app.models import Template, TemplateProblem
from app.tests.lib import create_user


# Test that a user can create a template problem for various difficulty levels.
@pytest.mark.django_db
@pytest.mark.parametrize("difficulty", ["A", "B", "C"])
def test_user_can_create_template_problem(client: Client, difficulty: str):
    user = create_user(client)
    template = Template(author=user, name="My template")
    template.save()

    client.force_login(user)
    response = client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "topic": "TestTopic",
            "difficulty": difficulty,
            "count": 2,
        },
    )
    # If there are no errors, a new TemplateProblem should have been created.
    assert TemplateProblem.objects.filter(template__pk=template.pk).exists()


# Test that creating a template problem with a count greater than the allowed maximum is rejected.
@pytest.mark.django_db
@pytest.mark.parametrize("difficulty", ["A", "B", "C"])
def test_user_can_not_create_template_problem_with_too_many_problems(
    client: Client, difficulty: str
):
    user = create_user(client)
    template = Template(author=user, name="My template")
    template.save()

    client.force_login(user)
    response = client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "topic": "TestTopic",
            "difficulty": difficulty,
            "count": 21,  # Assuming max_value is 20 based on your field validators
        },
    )
    # In case of a validation error, no new TemplateProblem should be created.
    assert not TemplateProblem.objects.filter(template__pk=template.pk).exists()


# Test that the user cannot create more than one template problem with the same topic and difficulty.
@pytest.mark.django_db
def test_user_can_not_create_template_problem_with_same_topic_and_difficulty_more_than_once_per_test(
    client: Client,
):
    user = create_user(client)
    template = Template(author=user, name="My template")
    template.save()

    client.force_login(user)
    # First POST with a given topic/difficulty should succeed.
    client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "topic": "TestTopic",
            "difficulty": "A",
            "count": 1,
        },
    )
    # Second POST with the same topic/difficulty should fail (raise a validation error).
    client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "topic": "TestTopic",
            "difficulty": "A",
            "count": 2,
        },
    )

    # Only one TemplateProblem record for ("TestTopic", "A") should exist.
    assert (
        TemplateProblem.objects.filter(
            template__pk=template.pk, topic="TestTopic", difficulty="A"
        ).count()
        == 1
    )
