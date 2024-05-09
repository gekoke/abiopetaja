from __future__ import annotations

import logging
import uuid
from base64 import b64encode
from typing import Iterable

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
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
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field
from typing_extensions import TYPE_CHECKING

from app.errors import (
    EmptyTemplate,
    PDFCompilationError,
    TestGenerationError,
)

logger = logging.getLogger(__name__)


class Entity(Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)

    class Meta:
        abstract = True


class ProblemKind(IntegerChoices):
    LINEAR_INEQUALITY = 1, _("Linear inequality")
    QUADRATIC_INEQUALITY = 2, _("Quadratic inequality")
    FRACTIONAL_INEQUALITY = 3, _("Fractional inequality")

    def generate(self) -> Problem:
        import app.maths as maths

        problem_generator = {
            ProblemKind.LINEAR_INEQUALITY: maths.make_linear_inequality_problem,
            ProblemKind.QUADRATIC_INEQUALITY: maths.make_quadratic_inequality_problem,
            ProblemKind.FRACTIONAL_INEQUALITY: maths.make_fractional_inequality_problem,
        }

        return problem_generator[self]()

    @staticmethod
    def get_problem_text(problem_kind: ProblemKind) -> str:
        PROBLEM_TEXT = {
            ProblemKind.LINEAR_INEQUALITY: _("Solve the following linear inequalities:"),
            ProblemKind.QUADRATIC_INEQUALITY: _("Solve the following quadratic inequalities:"),
            ProblemKind.FRACTIONAL_INEQUALITY: _("Solve the following fractional inequalities:"),
        }
        return PROBLEM_TEXT[problem_kind]


class TestGenerationParameters(BaseModel):
    test_version_count: int = Field(default=1, ge=1, le=6)


class Template(Entity):
    """A template is a collection of `ProblemKind` entities that can be rendered into a `Test`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        templateproblem_set = RelatedManager["TemplateProblem"]()

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)
    title = models.CharField(max_length=1000, blank=True)

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
    def generate_test(
        self, test_generation_parameters: TestGenerationParameters
    ) -> Test | TestGenerationError:
        test = Test()
        test.author = self.author
        test.is_saved = False
        test.title = self.title

        if not self.problem_count:
            return TestGenerationError(reason=EmptyTemplate())

        for i in range(test_generation_parameters.test_version_count):
            test_version = TestVersion()
            test_version.test = test
            test_version.version_number = i + 1

            for entry in self.templateproblem_set.all():
                for __ in range(entry.count):
                    problem_kind = ProblemKind(entry.problem_kind)
                    problem = problem_kind.generate()
                    problem.test_version = test_version
                    problem.save()

            match test_version.compile_pdf():
                case bytes() as pdf_bytes:
                    test_version.pdf.save(f"{test_version.id}.pdf", ContentFile(pdf_bytes))
                case PDFCompilationError() as error:
                    return TestGenerationError(reason=error)

            test_version.save()
            test.add_version(test_version)

        match test.compile_answer_key_pdf():
            case bytes() as pdf_bytes:
                test.answer_key_pdf.save(f"{test.id}.pdf", ContentFile(pdf_bytes))
            case PDFCompilationError() as error:
                return TestGenerationError(reason=error)

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
    # We add a default value so forms render nicer (don't have a empty placeholder '-----')
    problem_kind = IntegerField(choices=ProblemKind.choices, default=1)
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

    def __str__(self):
        return gettext(ProblemKind(self.problem_kind).label)


class TestVersion(Entity):
    """A version of a `Test`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        from app.pdf import PDFCompilationError

        problem_set = RelatedManager["Problem"]()

    test = ForeignKey("Test", on_delete=CASCADE)
    version_number = models.IntegerField(default=1)
    pdf = models.FileField()

    class Meta:
        unique_together = ["test", "version_number"]

    def problem_count(self) -> int:
        return self.problem_set.count()

    def compile_pdf(self) -> PDFCompilationError | bytes:
        from app.pdf import compile_test_version_pdf

        return compile_test_version_pdf(self)

    def pdf_b64_str(self) -> str:
        return b64encode(self.pdf.read()).decode("utf-8")


class Problem(Entity):
    kind = IntegerField(choices=ProblemKind.choices)
    definition = TextField()
    solution = TextField()
    test_version = ForeignKey(TestVersion, on_delete=CASCADE)

    @property
    def problem_text(self) -> str:
        return ProblemKind.get_problem_text(ProblemKind(self.kind))


class Test(Entity):
    """A test composed of documents rendered from a `Template`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        from app.pdf import PDFCompilationError

        testversion_set = RelatedManager[TestVersion]()

    author = ForeignKey(User, on_delete=CASCADE)
    name = models.CharField(max_length=255, validators=[MinLengthValidator(1)], null=True)
    is_saved = models.BooleanField(default=False)
    """
    Whether the test should be persisted.
    Any test that is not marked as saved is due for deletion.
    """
    title = models.CharField(max_length=1000, blank=True)
    answer_key_pdf = models.FileField()

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

    def compile_answer_key_pdf(self) -> PDFCompilationError | bytes:
        from app.pdf import compile_answer_key_pdf

        return compile_answer_key_pdf(self)

    def __str__(self):
        return self.name if self.name is not None else gettext("[Unnamed Test]")
