from http import HTTPStatus

import pytest
from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse

from app.annoying import get_object_or_None
from app.models import (
    Template,
    Test,
)
from app.tests.lib import create_user


@pytest.mark.django_db
def test_user_can_generate_a_test(client: Client):
    user = create_user(client)
    template = Template.objects.filter(author=user, name="Inequalities").first()
    assert template is not None

    client.force_login(user)
    client.post(
        reverse("app:test-generate"),
        {
            "template": template.pk,
            "test_version_count": 1,
        },
    )

    Test.objects.get(author=user)


@pytest.mark.django_db
def test_user_can_not_generate_an_empty_test(client: Client):
    user = create_user(client)
    client.post(reverse("app:template-create"), {"name": "empty template"})
    template: Template = Template.objects.get(author=user, name="empty template")
    assert template is not None

    client.force_login(user)
    client.post(
        reverse("app:test-generate"),
        {
            "template": template.pk,
            "test_version_count": 1,
        },
    )

    test = get_object_or_None(Test, author=user)
    assert test is None


@pytest.mark.django_db
def test_user_can_delete_test(client: Client):
    user = create_user(client)
    test = Test()
    test.author = user
    test.name = "Test"
    test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    test.is_saved = True

    client.force_login(user)
    client.post(reverse("app:test-delete", kwargs={"pk": test.pk}))

    assert not Test.objects.contains(test)


@pytest.mark.django_db
def test_user_can_save_test(client: Client):
    user = create_user(client)
    unsaved_test = Test()
    unsaved_test.author = user
    unsaved_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    unsaved_test.is_saved = False
    unsaved_test.save()

    client.force_login(user)
    client.post(
        reverse("app:test-save", kwargs={"pk": unsaved_test.pk}),
        {
            "name": "Fall test",
        },
    )

    test = Test.objects.get(pk=unsaved_test.pk)
    assert test.is_saved


@pytest.mark.django_db
def test_saved_test_has_input_name(client: Client):
    user = create_user(client)
    unsaved_test = Test()
    unsaved_test.author = user
    unsaved_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    unsaved_test.save()
    test_name = "Fall test"

    client.force_login(user)
    client.post(
        reverse("app:test-save", kwargs={"pk": unsaved_test.pk}),
        {
            "name": test_name,
        },
    )

    test = Test.objects.get(pk=unsaved_test.pk)
    assert test.name == test_name


@pytest.mark.django_db
def test_user_can_not_save_other_users_test(client: Client):
    alice = create_user(client)
    eve = create_user(client)
    alice_test = Test()
    alice_test.author = alice
    alice_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    alice_test.save()

    client.force_login(eve)
    response = client.post(
        reverse("app:test-save", kwargs={"pk": alice_test.pk}),
        {
            "name": "Get pwned",
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_user_can_not_save_test_with_nonunique_name(client: Client):
    user = create_user(client)
    existing_test = Test()
    existing_test.author = user
    existing_test.name = "Fall test"
    existing_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    existing_test.is_saved = True
    existing_test.save()
    new_test = Test()
    new_test.author = user
    new_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    new_test.save()

    client.force_login(user)
    client.post(
        reverse("app:test-save", kwargs={"pk": new_test.pk}),
        {
            "name": "Fall test",
        },
    )

    test = Test.objects.get(pk=new_test.pk)
    assert not test.is_saved


@pytest.mark.django_db
def test_unsaved_tests_are_deleted_after_test_generation(client: Client):
    user = create_user(client)
    unsaved_test = Test()
    unsaved_test.author = user
    unsaved_test.name = "Spring test"
    unsaved_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    unsaved_test.is_saved = False
    unsaved_test.save()
    template = Template.objects.filter(author=user, name="Inequalities").first()
    assert template is not None

    client.force_login(user)
    client.post(
        reverse("app:test-generate"),
        {
            "template": template.pk,
            "test_version_count": 1,
        },
    )

    assert not Test.objects.contains(unsaved_test)


@pytest.mark.django_db
def test_saved_tests_are_kept_after_test_generation(client: Client):
    user = create_user(client)
    saved_test = Test()
    saved_test.author = user
    saved_test.name = "Spring test"
    saved_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    saved_test.is_saved = True
    saved_test.save()
    template = Template.objects.filter(author=user, name="Inequalities").first()
    assert template is not None

    client.force_login(user)
    client.post(
        reverse("app:test-generate"),
        {
            "template": template.pk,
            "test_version_count": 1,
        },
    )

    assert Test.objects.contains(saved_test)


@pytest.mark.django_db
def test_unsaved_tests_of_other_users_are_kept_after_test_generation(client: Client):
    alice = create_user(client)
    bob = create_user(client)
    bob_test = Test()
    bob_test.author = bob
    bob_test.name = "Bob test"
    bob_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    bob_test.is_saved = False
    bob_test.save()
    template = Template.objects.filter(author=alice, name="Inequalities").first()
    assert template is not None

    client.force_login(alice)
    client.post(
        reverse("app:test-generate"),
        {
            "template": template.pk,
            "test_version_count": 1,
        },
    )

    assert Test.objects.contains(bob_test)


@pytest.mark.django_db
def test_saved_tests_of_other_users_are_kept_after_test_generation(client: Client):
    alice = create_user(client)
    bob = create_user(client)
    bob_test = Test()
    bob_test.author = bob
    bob_test.name = "Bob test"
    bob_test.answer_key_pdf.save("answers.pdf", ContentFile(""))
    bob_test.is_saved = True
    bob_test.save()
    template = Template.objects.filter(author=alice, name="Inequalities").first()
    assert template is not None

    client.force_login(alice)
    client.post(
        reverse("app:test-generate"),
        {
            "template": template.pk,
            "test_version_count": 1,
        },
    )

    assert Test.objects.contains(bob_test)
