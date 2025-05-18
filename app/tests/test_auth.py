from http import HTTPStatus
from urllib.parse import quote

import pytest
from django.test import Client
from django.urls import reverse
from pytest_django.asserts import assertRedirects


def test_unauthenticated_user_can_get_login_page(client: Client):
    res = client.get(reverse("account_login"), follow=True)
    assert res.status_code == HTTPStatus.OK


def test_unauthenticated_user_can_get_signup_page(client: Client):
    res = client.get(reverse("account_signup"), follow=True)
    assert res.status_code == HTTPStatus.OK


views = [
    "app:dashboard",
    "app:template-list",
    "app:template-create",
    "app:topic-difficulty-list",  # Updated view name
    "app:test-generation",
    "app:test-list",
    "app:test-generate",
    "app:userfeedback-create",
]


@pytest.mark.parametrize("view_name", views)
def test_unauthenticated_user_is_redirected_to_login_page_when_requesting_view(
    view_name: str, client: Client
):
    assertRedirects(
        response=client.get(reverse(view_name), follow=True),
        expected_url=reverse("account_login") + "?next=" + quote(reverse(view_name)),
    )


@pytest.mark.parametrize("view_name", views)
def test_authenticated_user_can_get_view(view_name: str, client: Client):
    response = client.get(reverse(view_name), follow=True)
    assert response.status_code == HTTPStatus.OK
