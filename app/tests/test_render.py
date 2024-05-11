import os
import random
import subprocess
from tempfile import TemporaryDirectory

import pytest
from django.test import Client
from django.urls import reverse

from app.models import ProblemKind, Template, Test, TestGenerationParameters, TestVersion
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
        subprocess.run(["pdftotext", pdf_file, txt_file])
        with open(txt_file) as f:
            return f.read()


@pytest.mark.django_db
def test_test_version_renders_as_expected(client: Client):
    random.seed(69)

    user = create_user(client)
    template = Template()
    template.author = user
    template.add_problem(ProblemKind.LINEAR_INEQUALITY, count=3)
    template.add_problem(ProblemKind.QUADRATIC_INEQUALITY, count=2)
    template.save()
    template.generate_test(TestGenerationParameters(test_version_count=1))
    test_version = TestVersion.objects.filter(test__author=user, version_number=1).first()
    assert test_version is not None
    expected_text = """Version 1
1) Solve the following linear inequalities:
a) 5 (x + 4) − 3 > 5 (x + 5) − 3 (x − 4)
b) 5 (x − 4) − 2 > 4 (x + 5) + 2 (x − 2)
c) 3 (x + 2) + 5 > 4 (x + 5) + 5 (x − 3)
2) Solve the following quadratic inequalities:
a) 2x2 − 6x − 6 < 0
b) 12x − 7 > 0"""

    response = client.get(reverse("app:testversion-download", kwargs={"pk": test_version.pk}))

    pdf_text = _extract_pdf_text(response.content)
    print(expected_text)
    print(pdf_text)
    assert expected_text in pdf_text


@pytest.mark.django_db
def test_test_answer_key_renders_as_expected(client: Client):
    random.seed(420)

    user = create_user(client)
    template = Template()
    template.author = user
    template.add_problem(ProblemKind.QUADRATIC_INEQUALITY, count=1)
    template.save()
    template.generate_test(TestGenerationParameters(test_version_count=1))
    test = Test.objects.filter(author=user).first()
    assert test is not None
    expected_text = """Version 1
1) Solve the following quadratic inequalities:
a) (−∞, ∞)"""

    response = client.get(reverse("app:test-download", kwargs={"pk": test.pk}))

    pdf_text = _extract_pdf_text(response.content)
    assert expected_text in pdf_text
