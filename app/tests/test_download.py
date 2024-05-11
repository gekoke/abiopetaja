from http import HTTPStatus

import pytest
from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse

from app.models import (
    ProblemKind,
    Template,
    Test,
    TestGenerationParameters,
    TestVersion,
)
from app.tests.lib import create_user


@pytest.mark.django_db
def test_user_can_download_test_version(client: Client):
    user = create_user(client)
    template = Template()
    template.author = user
    template.add_problem(ProblemKind.FRACTIONAL_INEQUALITY, count=2)
    template.save()
    template.generate_test(TestGenerationParameters(test_version_count=2))
    test_version = TestVersion.objects.filter(test__author=user).first()
    assert test_version is not None
    expected_data = test_version.pdf.read()

    client.force_login(user)
    response = client.get(reverse("app:testversion-download", kwargs={"pk": test_version.pk}))

    assert response.content == expected_data


@pytest.mark.django_db
def test_user_can_not_download_other_users_test_version(client: Client):
    alice = create_user(client)
    eve = create_user(client)
    template = Template()
    template.author = alice
    template.add_problem(ProblemKind.FRACTIONAL_INEQUALITY, count=2)
    template.save()
    template.generate_test(TestGenerationParameters(test_version_count=2))
    test_version = TestVersion.objects.filter(test__author=alice).first()
    assert test_version is not None

    client.force_login(eve)
    response = client.get(reverse("app:testversion-download", kwargs={"pk": test_version.pk}))

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_user_can_download_test_answer_key(client: Client):
    user = create_user(client)
    answer_key_data = b"foobar"
    test = Test()
    test.author = user
    test.name = "Test"
    test.answer_key_pdf.save("answers.pdf", ContentFile(answer_key_data))
    test.is_saved = True
    test.save()

    client.force_login(user)
    response = client.get(reverse("app:test-download", kwargs={"pk": test.pk}))

    assert response.content == answer_key_data


@pytest.mark.django_db
def test_user_can_not_download_other_users_test_answer_key(client: Client):
    alice = create_user(client)
    eve = create_user(client)
    test = Test()
    test.author = alice
    test.name = "Test"
    test.answer_key_pdf.save("answers.pdf", ContentFile("foobar"))
    test.is_saved = True
    test.save()

    client.force_login(eve)
    response = client.get(reverse("app:test-download", kwargs={"pk": test.pk}))

    assert response.status_code == HTTPStatus.NOT_FOUND
