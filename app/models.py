from __future__ import annotations

import logging
import random
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
from sympy import Expr, S, simplify, solveset, sympify
from sympy.core import UnevaluatedExpr, symbols
from sympy.printing.latex import latex
from typing_extensions import TYPE_CHECKING

from app.errors import (
    EmptyTemplate,
    TestGenerationError,
)
from app.pdf import PDFCompilationError, compile_pdf
from app.render import render_answer_key, render_test_version

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
            ProblemKind.LINEAR_INEQUALITY: make_linear_inequality_problem,
            ProblemKind.QUADRATIC_INEQUALITY: make_quadratic_inequality_problem,
            ProblemKind.FRACTIONAL_INEQUALITY: make_fractional_inequality_problem,
            ProblemKind.EXPONENT_REDUCTION_PROBLEM: make_exponent_reduction_problem,
            ProblemKind.EXPONENT_OPERATION_PROBLEM: make_exponent_operation_problem,
        }

        return problem_generator[self]()

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


def _latex(expr):
    return latex(expr, decimal_separator="comma")


class Problem:
    kind: ProblemKind
    definition: str
    solution: str


def make_plus_or_minus():
    return random.choice(["+", "-"])


def make_comparison_operator(allow_eq: bool = True):
    """allow_eq: Whether to allow generating the '=' operator."""
    return random.choice(["<", "<=", ">=", ">"] + (["=="] if allow_eq else []))


def make_quadratic() -> Expr:
    def make_coeffiecient():
        return random.randint(-12, 12)

    a, b, c = make_coeffiecient(), make_coeffiecient(), make_coeffiecient()
    op1, op2 = make_plus_or_minus(), make_plus_or_minus()
    return sympify(f"{a}*x**2 {op1} {b}*x {op2} {c}", evaluate=False)


def make_fraction() -> Expr:
    """
    Make a fraction.

    Example:
    -------
    4*(x - 2) / (x + 3)
    """

    def make_coeffiecient():
        return random.randint(1, 8)

    c1, c2, c3 = (make_coeffiecient() for _ in range(3))
    op1, op2 = make_plus_or_minus(), make_plus_or_minus()
    # Use empty string if c1==1 to avoid multiplying by 1.
    c1 = "" if c1 == 1 else f"{c1}*"
    return sympify(f"{c1}(x {op1} {c2}) / (x {op2} {c3})", evaluate=False)


def make_linear_inequality_problem() -> TestVersionProblem:
    """
    Make a linear inequality problem.

    Example:
    -------
    `2(x - 3) - 1 > 3(x - 2) - 4(x + 1)`.
    """

    def make_coefficient():
        return random.randint(2, 5)

    c1, c2, c3, c4, c5, c6, c7 = (make_coefficient() for _ in range(7))
    o1, o2, o3, o4, o5 = (make_plus_or_minus() for _ in range(5))
    comparison = make_comparison_operator(allow_eq=False)

    problem_definition = sympify(
        f"{c1}*(x {o1} {c2}) {o2} {c3} {comparison} {c4}*(x {o3} {c5}) {o4} {c6}*(x {o5} {c7})",
        evaluate=False,
    )
    problem_solution = solveset(problem_definition, "x", S.Reals)

    problem = TestVersionProblem()
    problem.definition = _latex(problem_definition)
    problem.solution = _latex(problem_solution)
    problem.kind = ProblemKind.LINEAR_INEQUALITY
    return problem


def make_quadratic_inequality_problem() -> TestVersionProblem:
    """
    Make a quadratic inequality problem.

    Example:
    -------
    `-5x**2 + 9x + 2 > 0`.
    """
    quadratic = make_quadratic()
    comparison = make_comparison_operator(allow_eq=False)

    problem_definition = sympify(f"{quadratic} {comparison} 0")
    problem_solution = solveset(problem_definition, "x", S.Reals)

    problem = TestVersionProblem()
    problem.definition = _latex(problem_definition)
    problem.solution = _latex(problem_solution)
    problem.kind = ProblemKind.QUADRATIC_INEQUALITY
    return problem


def make_fractional_inequality_problem() -> TestVersionProblem:
    """
    Make a fractional inequality problem.

    Example:
    -------
    `2*(x - 2) / (x + 2) > 4`.
    """
    fraction = make_fraction()
    comparsion = make_comparison_operator(allow_eq=False)

    problem_definition = sympify(f"{fraction} {comparsion} {random.randint(-9, 9)}", evaluate=False)
    problem_solution = solveset(problem_definition, "x", S.Reals)

    problem = TestVersionProblem()
    problem.definition = _latex(problem_definition)
    problem.solution = _latex(problem_solution)
    problem.kind = ProblemKind.FRACTIONAL_INEQUALITY
    return problem


def make_exponent_reduction_problem() -> TestVersionProblem:
    m, n, w, x, y = symbols("m n w x y")

    def variant_1() -> TestVersionProblem:
        coef_1 = random.randint(10, 50)
        coef_2 = random.randint(10, 50)
        exp_1 = random.randint(2, 9)
        exp_2 = random.randint(2, 9)
        exp_3 = random.randint(2, 9)
        exp_4 = random.randint(2, 9)
        exp_5 = random.randint(2, 9)
        exp_6 = random.randint(2, 9)

        numerator = UnevaluatedExpr(coef_1 * w**exp_1 * x**exp_2 * y**exp_3)
        denominator = coef_2 * w**exp_4 * x**exp_5 * y**exp_6

        problem_definition = numerator / denominator
        problem_solution = simplify(problem_definition)

        problem = TestVersionProblem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_REDUCTION_PROBLEM
        return problem

    def variant_2() -> TestVersionProblem:
        coef_1 = random.randint(10, 50)
        coef_2 = random.randint(10, 50)
        exp_1 = random.randint(2, 9)
        exp_2 = random.randint(2, 9)
        exp_4 = random.randint(2, 9)
        exp_5 = random.randint(2, 9)

        numerator = UnevaluatedExpr(coef_1 * m**exp_1 * n**exp_2)
        denominator = coef_2 * m**exp_4 * n**exp_5

        problem_definition = numerator / denominator
        problem_solution = simplify(problem_definition)

        problem = TestVersionProblem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_REDUCTION_PROBLEM
        return problem

    variants = [
        variant_1,
        variant_2,
    ]
    return random.choice(variants)()


def make_exponent_operation_problem() -> TestVersionProblem:
    u, v, x, y, z = symbols("u v x y z")

    def variant_1() -> TestVersionProblem:
        coef_1 = random.choice(list(range(-9, 0)) + list(range(1, 9)))
        coef_2 = random.randint(1, 9)
        exp = random.randint(2, 3)
        numerator = UnevaluatedExpr(coef_1 * x * z)
        denominator = coef_2 * y

        problem_definition = UnevaluatedExpr(numerator / denominator) ** exp
        problem_solution = simplify(problem_definition)

        problem = TestVersionProblem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    def variant_2() -> TestVersionProblem:
        coef_1 = random.choice(list(i / 10 for i in range(1, 10)))
        coef_2 = random.randint(2, 9)
        exp_1 = random.randint(2, 3)
        exp_2 = random.randint(2, 3)
        exp_3 = random.randint(2, 3)

        fact_1 = UnevaluatedExpr(coef_1 * x**exp_1 * y**exp_2)
        fact_2 = coef_2 * x * y**exp_3

        problem_definition = fact_1 * fact_2
        problem_solution = simplify(problem_definition)

        problem = TestVersionProblem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    def variant_3() -> TestVersionProblem:
        coef_1 = random.randint(-4, -2)
        coef_2 = random.randint(2, 6)
        exp_1 = random.randint(2, 4)
        exp_2 = random.randint(2, 4)

        problem_definition = UnevaluatedExpr(coef_1 * u * v**exp_1) / (coef_2 * u * v**exp_2)
        problem_solution = simplify(problem_definition)

        problem = TestVersionProblem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    def variant_4() -> TestVersionProblem:
        exp_1 = random.randint(1, 3)
        exp_2 = random.randint(2, 3)
        exp_3 = random.randint(2, 3)

        problem_definition = (UnevaluatedExpr(x**exp_1 * y**exp_2) ** exp_3) * (-x * y)
        problem_solution = simplify(problem_definition)

        problem = TestVersionProblem()
        problem.definition = _latex(problem_definition)
        problem.solution = _latex(problem_solution)
        problem.kind = ProblemKind.EXPONENT_OPERATION_PROBLEM
        return problem

    variants = [
        variant_1,
        variant_2,
        variant_3,
        variant_4,
    ]
    return random.choice(variants)()
