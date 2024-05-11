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
def test_updated_template_has_updated_fields(client: Client):
    template_title = "My title"
    updated_title = "Updated title"
    user = create_user(client)
    client.force_login(user)
    client.post(reverse("app:template-create"), {"name": "My template", "title": template_title})
    template: Template = Template.objects.get(author=user, name="My template")

    client.force_login(user)
    client.post(
        reverse("app:template-update", kwargs={"pk": template.pk}), {"title": updated_title}
    )

    template: Template = Template.objects.get(author=user, name="My template")
    assert template.title == updated_title


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
