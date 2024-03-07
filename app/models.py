from __future__ import annotations

import base64
import logging
import os
import uuid
from subprocess import CalledProcessError, TimeoutExpired, run
from tempfile import TemporaryDirectory
from typing import Iterable

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import (
    CASCADE,
    CheckConstraint,
    ForeignKey,
    IntegerChoices,
    IntegerField,
    Model,
    PositiveIntegerField,
    Q,
    TextField,
)
from django.urls import reverse
from django.utils.translation import gettext
from pydantic import BaseModel, Field
from typing_extensions import TYPE_CHECKING

logger = logging.getLogger(__name__)


class Entity(Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)

    class Meta:
        abstract = True


class ProblemKind(IntegerChoices):
    LINEAR_INEQUALITY = 1, gettext("Linear inequality")
    QUADRATIC_INEQUALITY = 2, gettext("Quadratic inequality")

    def generate(self) -> Problem:
        import app.maths as maths

        problem_generator = {
            ProblemKind.LINEAR_INEQUALITY: maths.make_linear_inequality_problem,
            ProblemKind.QUADRATIC_INEQUALITY: maths.make_quadratic_inequality_problem,
        }

        return problem_generator[self]()


class RenderError:
    pass


class File(Entity):
    data = models.BinaryField()

    def as_base64(self) -> str:
        return base64.b64encode(self.data).decode("utf-8")


class TestGenerationParameters(BaseModel):
    test_version_count: int = Field(default=1, ge=1, le=6)


class Template(Entity):
    """A template is a collection of `ProblemKind` entities that can be rendered into a `Test`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        templateproblem_set = RelatedManager["TemplateProblem"]()

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)

    class Meta:
        unique_together = ["author", "name"]

    def get_absolute_url(self) -> str:
        return reverse("app:template-detail", kwargs={"pk": self.pk})

    @property
    def problem_count(self) -> int:
        return TemplateProblem.objects.filter(template=self).count()

    @property
    def problem_kinds(self) -> Iterable[ProblemKind]:
        return [ProblemKind(entry.problem_kind) for entry in self.templateproblem_set.all()]

    @property
    def problem_kind_labels(self) -> Iterable[str]:
        return [kind.label for kind in self.problem_kinds]

    @transaction.atomic
    def add_problem(self, kind: ProblemKind, count: int = 1):
        entry = TemplateProblem()
        entry.template = self
        entry.problem_kind = kind
        entry.count = count
        entry.save()

    @transaction.atomic
    def generate_test(self, test_generation_parameters: TestGenerationParameters) -> Test:
        test = Test()
        test.author = self.author
        test.is_saved = False

        for i in range(test_generation_parameters.test_version_count):
            test_version = TestVersion()
            test_version.test = test
            test_version.version_number = i + 1
            test_version.save()

            for entry in self.templateproblem_set.all():
                for _ in range(entry.count):
                    problem_kind = ProblemKind(entry.problem_kind)
                    problem = problem_kind.generate()
                    problem.test_version = test_version
                    problem.save()

            test.add_version(test_version)

        test.save()
        return test

    @property
    def entries(self):
        return self.templateproblem_set.all()

    def __str__(self) -> str:
        return self.name


class TemplateProblem(Entity):
    """A `ProblemKind` instance in the given `Template`."""

    template = ForeignKey(Template, on_delete=CASCADE)
    problem_kind = IntegerField(choices=ProblemKind.choices)
    count = PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(20),
        ]
    )
    """
    The number of times the problem should appear in the test
    """

    class Meta:
        unique_together = ["template", "problem_kind"]

    @property
    def problem_kind_label(self):
        return ProblemKind(self.problem_kind).label

    def __str__(self):
        return ProblemKind(self.problem_kind).label


class TestVersion(Entity):
    """A version of a `Test`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        problem_set = RelatedManager["Problem"]()

    test = ForeignKey("Test", on_delete=CASCADE)
    version_number = models.IntegerField(default=1)

    class Meta:
        unique_together = ["test", "version_number"]

    def problem_count(self) -> int:
        return self.problem_set.count()

    def render(self) -> RenderError | File:
        return self._render_to_pdf(self._as_latex())

    def _as_latex(self) -> str:
        latex = """
        \\documentclass{article}
        \\usepackage{amsfonts}
        \\begin{document}
        """

        for problem in self.problem_set.all():
            latex += problem.render()

        latex += "\\end{document}"

        return latex

    def _render_to_pdf(self, latex_source: str) -> RenderError | File:
        with TemporaryDirectory() as tmp_dir:
            tex_file = os.path.join(tmp_dir, "template.tex")
            pdf_file = os.path.join(tmp_dir, "template.pdf")
            with open(tex_file, "w") as file:
                file.write(latex_source)

            logger.info(latex_source)
            try:
                run(["pdflatex", tex_file], cwd=tmp_dir, timeout=3, check=True)
            except TimeoutExpired:
                logger.error(f"pdflatex timed out for {self}")
                return RenderError()
            except CalledProcessError as e:
                logger.error(f"pdflatex failed for {self}, {e}")
                return RenderError()

            try:
                with open(pdf_file, "rb") as file:
                    pdf_file = File()
                    pdf_file.data = file.read()
            except FileNotFoundError:
                logger.error(f"pdflatex did not produce a PDF for {self}")
                return RenderError()

        return pdf_file


class Problem(Entity):
    kind = IntegerField(choices=ProblemKind.choices)
    definition = TextField()
    solution = TextField()
    test_version = ForeignKey(TestVersion, on_delete=CASCADE)

    def render(self) -> str:
        return f"""
        Definition: $${self.definition}$$
        Solution: $${self.solution}$$
        """


class Test(Entity):
    """A test composed of documents rendered from a `Template`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        testversion_set = RelatedManager[TestVersion]()

    author = ForeignKey(User, on_delete=CASCADE)
    name = models.CharField(max_length=255, validators=[MinLengthValidator(1)], null=True)
    is_saved = models.BooleanField(default=False)
    """
    Whether the test should be persisted.
    Any test that is not marked as saved is due for deletion.
    """

    class Meta:
        unique_together = [["author", "name"]]

        constraints = [
            CheckConstraint(
                check=Q(is_saved=False) | Q(name__isnull=False),
                name="saved_test_has_name",
            ),
        ]

    @property
    def version_count(self) -> int:
        return self.testversion_set.count()

    @property
    def versions(self) -> Iterable[TestVersion]:
        return self.testversion_set.all()

    def get_absolute_url(self) -> str:
        return reverse("app:test-detail", kwargs={"pk": self.pk})

    def add_version(self, test_version: TestVersion) -> None:
        self.testversion_set.add(test_version)

    def __str__(self):
        return self.name if self.name is not None else gettext("[Unnamed Test]")
