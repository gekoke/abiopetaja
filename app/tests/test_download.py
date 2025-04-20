import os
import random
import subprocess
from tempfile import TemporaryDirectory

import pytest
from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse

from app.models import Template, Test, TestGenerationParameters, TestVersion
from app.tests.lib import create_user


def _extract_pdf_text(pdf_data: bytes) -> str:
    """
    Extract text from bytes interpreted as a PDF file.
    Depends on `pdftotext` being in the system PATH.
    """
    with TemporaryDirectory() as tmp_dir:
        pdf_file = os.path.join(tmp_dir, "testversion.pdf")
        txt_file = os.path.join(tmp_dir, "text.txt")
        with open(pdf_file, "wb") as f:
            f.write(pdf_data)
        subprocess.run(["pdftotext", pdf_file, txt_file], check=True)
        with open(txt_file) as f:
            return f.read()


@pytest.mark.django_db
def test_user_can_download_test_version(client: Client):
    random.seed(69)

    user = create_user(client)
    template = Template(author=user, name="Minu mall")
    # Use topics from your database. For a "fractional inequality" equivalent, we choose the topic
    # "VÕRRATUSED JA VÕRRATUSESÜSTEEMID" with difficulty "B" (e.g. for rational inequalities).
    template.add_problem(topic="VÕRRATUSED JA VÕRRATUSESÜSTEEMID", difficulty="B", count=2)
    template.save()
    template.generate_test(TestGenerationParameters(test_version_count=2))
    test_version = TestVersion.objects.filter(test__author=user, version_number=1).first()
    assert test_version is not None
    expected_data = test_version.pdf.read()

    client.force_login(user)
    response = client.get(reverse("app:testversion-download", kwargs={"pk": test_version.pk}))
    assert response.content == expected_data


@pytest.mark.django_db
def test_user_can_not_download_other_users_test_version(client: Client):
    alice = create_user(client)
    eve = create_user(client)
    template = Template(author=alice, name="Minu mall")
    # Again, we use the topic "VÕRRATUSED JA VÕRRATUSESÜSTEEMID" with difficulty "B".
    template.add_problem(topic="VÕRRATUSED JA VÕRRATUSESÜSTEEMID", difficulty="B", count=2)
    template.save()
    template.generate_test(TestGenerationParameters(test_version_count=2))
    test_version = TestVersion.objects.filter(test__author=alice, version_number=1).first()
    assert test_version is not None

    client.force_login(eve)
    response = client.get(reverse("app:testversion-download", kwargs={"pk": test_version.pk}))
    assert response.status_code == 404  # Not found for another user's test version


@pytest.mark.django_db
def test_user_can_download_test_answer_key(client: Client):
    user = create_user(client)
    answer_key_data = b"foobar"
    test = Test(author=user, name="Test")
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
    test = Test(author=alice, name="Test")
    test.answer_key_pdf.save("answers.pdf", ContentFile(b"foobar"))
    test.is_saved = True
    test.save()

    client.force_login(eve)
    response = client.get(reverse("app:test-download", kwargs={"pk": test.pk}))
    assert response.status_code == 404
