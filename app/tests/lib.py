import random
import string

from django.test import Client
from django.urls import reverse

from app.models import User


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
