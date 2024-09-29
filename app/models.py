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
from django.db.models.constraints import UniqueConstraint
from django.urls import reverse
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field
from typing_extensions import TYPE_CHECKING

import app.math
from app.latex import render_answer_key, render_test_version
from app.pdf import PDFCompilationError, compile_pdf

logger = logging.getLogger(__name__)


class Entity(Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ProblemKind(IntegerChoices):
    LINEAR_INEQUALITY = 1, _("Linear inequality")
    QUADRATIC_INEQUALITY = 2, _("Quadratic inequality")
    FRACTIONAL_INEQUALITY = 3, _("Fractional inequality")
    EXPONENT_REDUCTION_PROBLEM = 4, _("Exponent reduction problem")
    EXPONENT_OPERATION_PROBLEM = 5, _("Exponent operation problem")

    def generate(self) -> TestVersionProblem:
        problem_generator = {
            ProblemKind.LINEAR_INEQUALITY: app.math.make_linear_inequality_problem,
            ProblemKind.QUADRATIC_INEQUALITY: app.math.make_quadratic_inequality_problem,
            ProblemKind.FRACTIONAL_INEQUALITY: app.math.make_fractional_inequality_problem,
            ProblemKind.EXPONENT_REDUCTION_PROBLEM: app.math.make_exponent_reduction_problem,
            ProblemKind.EXPONENT_OPERATION_PROBLEM: app.math.make_exponent_operation_problem,
        }
        generated_problem = problem_generator[self]()

        problem = TestVersionProblem()
        problem.kind = self
        problem.definition = generated_problem.definition
        problem.solution = generated_problem.solution
        return problem

    @staticmethod
    def get_problem_text(problem_kind: ProblemKind) -> str:
        PROBLEM_TEXT = {
            ProblemKind.LINEAR_INEQUALITY: _("Solve the following linear inequalities:"),
            ProblemKind.QUADRATIC_INEQUALITY: _("Solve the following quadratic inequalities:"),
            ProblemKind.FRACTIONAL_INEQUALITY: _("Solve the following fractional inequalities:"),
            ProblemKind.EXPONENT_REDUCTION_PROBLEM: _("Reduce the following expressions:"),
            ProblemKind.EXPONENT_OPERATION_PROBLEM: _("Perform the following operations:"),
        }
        return PROBLEM_TEXT[problem_kind]


class TestGenerationParameters(BaseModel):
    test_version_count: int = Field(default=1, ge=1, le=6)


type TestGenerationError = EmptyTemplate | PDFCompilationError


class EmptyTemplate:
    pass


class Template(Entity):
    """A template is a collection of `ProblemKind` entities that can be rendered into a `Test`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        templateproblem_set = RelatedManager["TemplateProblem"]()

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(
        _("Name"), max_length=255, blank=False, help_text=_("Only you can see this name")
    )
    title = models.TextField(
        blank=True,
        verbose_name=pgettext_lazy("of a template", "Title"),
        help_text=_(
            "Anything you add to this field will be rendered at the top of the test document"
        ),
    )

    class Meta:
        constraints = [
            UniqueConstraint(fields=["author", "name"], name="template_name_is_unique_per_author")
        ]

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
            return EmptyTemplate()

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
                case bytes() | bytearray() | memoryview() as pdf_bytes:
                    test_version.pdf.save(f"{test_version.id}.pdf", ContentFile(pdf_bytes))
                case _ as err:
                    return err

            test_version.save()
            test.add_version(test_version)

        match test.compile_answer_key_pdf():
            case bytes() | bytearray() | memoryview() as pdf_bytes:
                test.answer_key_pdf.save(f"{test.id}.pdf", ContentFile(pdf_bytes))
            case _ as err:
                return err

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
        constraints = [
            UniqueConstraint(
                fields=["template", "problem_kind"],
                name="problemkind_only_appears_once_per_template",
            )
        ]

    def __str__(self):
        return gettext(ProblemKind(self.problem_kind).label)


class TestVersion(Entity):
    """A version of a `Test`."""

    if TYPE_CHECKING:  # Add missing type hints.
        from django.db.models.manager import RelatedManager

        from app.pdf import PDFCompilationError

        testversionproblem_set = RelatedManager["TestVersionProblem"]()

    test = ForeignKey("Test", on_delete=CASCADE)
    version_number = models.IntegerField(default=1)
    pdf = models.FileField()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["test", "version_number"],
                name="test_does_not_have_any_testversion_number_more_than_once",
            )
        ]

    def problem_count(self) -> int:
        return self.testversionproblem_set.count()

    def compile_pdf(self) -> PDFCompilationError | bytes:
        return compile_pdf(render_test_version(self))

    def pdf_b64_str(self) -> str:
        return b64encode(self.pdf.read()).decode("utf-8")


class TestVersionProblem(Entity):
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
    name = models.CharField(
        _("Name"),
        max_length=255,
        validators=[MinLengthValidator(1)],
        null=True,
    )
    is_saved = models.BooleanField(default=False)
    """
    Whether the test should be persisted.
    Any test that is not marked as saved is due for deletion.
    """
    title = models.CharField(max_length=1000, blank=True)
    answer_key_pdf = models.FileField()

    class Meta:
        constraints = [
            UniqueConstraint(fields=["author", "name"], name="test_name_is_unique_per_author"),
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

    def answer_key_pdf_b64_str(self) -> str:
        return b64encode(self.answer_key_pdf.read()).decode("utf-8")

    def compile_answer_key_pdf(self) -> PDFCompilationError | bytes:
        return compile_pdf(render_answer_key(self))

    def __str__(self):
        return self.name if self.name is not None else gettext("[Unnamed Test]")


class UserFeedback(Entity):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = TextField(pgettext_lazy("of a user feedback", "Content"), blank=False)
