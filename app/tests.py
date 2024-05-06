import random
import string
from http import HTTPStatus
from urllib.parse import quote

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.translation import activate
from pytest_django.asserts import assertRedirects

from app.annoying import get_object_or_None
from app.models import Template, Test, User


@pytest.fixture(autouse=True)
def set_default_language():
    activate("en")


def create_user(client: Client):
    rand1 = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
    rand2 = "".join(random.choices(string.ascii_uppercase + string.digits, k=32))
    username, password = f"username_{rand1}", f"password_{rand2}"
    client.logout()
    client.post(
        reverse("account_signup"),
        {
            "username": username,
            "password1": password,
            "password2": password,
            "email": "",
        },
    )
    return User.objects.get(username=username)


def test_unauthenticated_user_can_get_login_page(client: Client):
    res = client.get(reverse("account_login"), follow=True)
    assert res.status_code == HTTPStatus.OK


def test_unauthenticated_user_can_get_signup_page(client: Client):
    res = client.get(reverse("account_signup"), follow=True)
    assert res.status_code == HTTPStatus.OK


login_required_views = [
    # only views that don't take an argument in their path
    "app:dashboard",
    "app:template-list",
    "app:template-create",
    "app:problemkind-list",
    "app:test-generation",
    "app:test-list",
    "app:test-generate",
]


@pytest.mark.parametrize("view_name", login_required_views)
def test_unauthenticated_user_is_redirected_to_login_page_when_requesting_view(
    view_name: str, client: Client
):
    assertRedirects(
        response=client.get(reverse(view_name), follow=True),
        expected_url=reverse("account_login") + "?next=" + quote(reverse(view_name)),
    )


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


@pytest.mark.django_db
def test_user_can_generate_a_test(client: Client):
    user = create_user(client)
    client.force_login(user)
    template = Template.objects.filter(author=user, name="Inequalities").first()
    assert template is not None

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
    client.force_login(user)
    client.post(reverse("app:template-create"), {"name": "empty template"})
    template: Template = Template.objects.get(author=user, name="empty template")
    assert template is not None

    client.post(
        reverse("app:test-generate"),
        {
            "template": template.pk,
            "test_version_count": 1,
        },
    )

    test = get_object_or_None(Test, author=user)
    assert test is None
