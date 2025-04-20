from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

from app.models import Template
from app.tests.lib import create_user


@pytest.mark.django_db
def test_user_can_create_a_template(client: Client):
    user = create_user(client)

    client.force_login(user)
    client.post(reverse("app:template-create"), {"name": "My template"})

    Template.objects.get(author=user, name="My template")


@pytest.mark.django_db
def test_created_template_has_input_name(client: Client):
    template_name = "My template"
    user = create_user(client)

    client.force_login(user)
    client.post(reverse("app:template-create"), {"name": template_name})

    template: Template = Template.objects.get(author=user, name=template_name)
    assert template.name == template_name


@pytest.mark.django_db
def test_created_template_has_input_fields(client: Client):
    template_title = "My title"
    user = create_user(client)

    client.force_login(user)
    client.post(reverse("app:template-create"), {"name": "My template", "title": template_title})

    template: Template = Template.objects.get(author=user, name="My template")
    assert template.title == template_title


@pytest.mark.django_db
def test_can_update_template_name(client: Client):
    template_data = {"name": "Initial name", "title": "Template title"}
    expected_name = "New name!"
    user = create_user(client)
    client.force_login(user)
    client.post(reverse("app:template-create"), template_data)
    template: Template = Template.objects.get(author=user, name=template_data["name"])

    template_data.update(name=expected_name)
    client.force_login(user)
    client.post(reverse("app:template-update", kwargs={"pk": template.pk}), template_data)

    template: Template = Template.objects.get(pk=template.pk)
    assert template.name == expected_name


@pytest.mark.django_db
def test_can_update_template_title(client: Client):
    template_data = {"name": "Template name", "title": "Initial title"}
    expected_title = "New title!"
    user = create_user(client)
    client.force_login(user)
    client.post(reverse("app:template-create"), template_data)
    template: Template = Template.objects.get(author=user, name=template_data["name"])

    template_data.update(title=expected_title)
    client.force_login(user)
    client.post(reverse("app:template-update", kwargs={"pk": template.pk}), template_data)

    template: Template = Template.objects.get(pk=template.pk)
    assert template.title == expected_title


@pytest.mark.django_db
def test_can_not_update_template_title_to_existing_title(client: Client):
    user = create_user(client)
    template_1 = Template()
    template_1.author = user
    template_1.name = "Template 1"
    template_1.title = "Important test"
    template_1.save()
    template_2 = Template()
    template_2.author = user
    template_2.name = "Template 2"
    template_2.title = "Important test"
    template_2.save()
    expected_name = template_1.name

    client.force_login(user)
    update_data = {"name": template_2.name, "title": template_1.title}
    client.post(reverse("app:template-update", kwargs={"pk": template_1.pk}), update_data)

    template_1 = Template.objects.get(pk=template_1.pk)
    assert template_1.name == expected_name


@pytest.mark.django_db
def test_user_can_get_created_template(client: Client):
    user = create_user(client)

    client.force_login(user)
    client.post(reverse("app:template-create"), {"name": "My template"})
    template: Template = Template.objects.get(author=user, name="My template")
    response = client.get(reverse("app:template-detail", kwargs={"pk": template.pk}))

    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_user_can_not_get_other_users_template(client: Client):
    alice = create_user(client)
    eve = create_user(client)
    template: Template = Template.objects.create(author=alice)

    client.force_login(eve)
    response = client.get(reverse("app:template-detail", kwargs={"pk": template.pk}))

    assert response.status_code == HTTPStatus.NOT_FOUND
