import pytest
from django.test import Client
from django.urls import reverse

from app.models import (
    ProblemKind,
    Template,
    TemplateProblem,
)
from app.tests.lib import create_user


@pytest.mark.django_db
@pytest.mark.parametrize("problem_kind", ProblemKind.values)
def test_user_can_create_template_problem(client: Client, problem_kind: ProblemKind):
    user = create_user(client)
    template = Template()
    template.author = user
    template.name = "My template"
    template.save()

    client.force_login(user)
    client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "problem_kind": problem_kind,
            "count": 2,
        },
    )

    assert TemplateProblem.objects.filter(template__pk=template.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("problem_kind", ProblemKind.values)
def test_user_can_not_create_template_problem_with_too_many_problems(
    client: Client, problem_kind: ProblemKind
):
    user = create_user(client)
    template = Template()
    template.author = user
    template.name = "My template"
    template.save()

    client.force_login(user)
    client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "problem_kind": problem_kind,
            "count": 21,
        },
    )

    assert not TemplateProblem.objects.filter(template__pk=template.pk).exists()


@pytest.mark.django_db
def test_user_can_not_create_template_problem_with_same_problem_kind_more_than_once_per_test(
    client: Client,
):
    user = create_user(client)
    template = Template()
    template.author = user
    template.name = "My template"
    template.save()

    client.force_login(user)
    client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "problem_kind": ProblemKind.FRACTIONAL_INEQUALITY,
            "count": 1,
        },
    )
    client.post(
        reverse("app:templateproblem-create", kwargs={"template_pk": template.pk}),
        {
            "problem_kind": ProblemKind.FRACTIONAL_INEQUALITY,
            "count": 2,
        },
    )

    assert TemplateProblem.objects.filter(template__pk=template.pk).count() == 1
