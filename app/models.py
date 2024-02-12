from __future__ import annotations

import base64
import logging
import uuid
from subprocess import TimeoutExpired, run
from tempfile import TemporaryDirectory
from typing import Iterable

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import (
    CASCADE,
    ForeignKey,
    IntegerChoices,
    IntegerField,
    Model,
    TextField,
)
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class Entity(Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)

    class Meta:
        abstract = True


class ProblemKind(IntegerChoices):
    LINEAR_INEQUALITY = 1, _("Linear inequality")
    QUADRATIC_INEQUALITY = 2, _("Quadratic inequality")

    def generate(self) -> Problem:
        import app.maths as maths

        problem_generator = {
            ProblemKind.LINEAR_INEQUALITY: maths.make_linear_inequality_problem,
            ProblemKind.QUADRATIC_INEQUALITY: maths.make_quadratic_inequality_problem,
        }

        return problem_generator[self]()


class Problem(Entity):
    kind = IntegerField(choices=ProblemKind.choices)
    definition = TextField()
    solution = TextField()


class RenderError:
    pass


class Template(Entity):
    """
    A template is a collection of `ProblemKind` entities
    that can be rendered into a `Test`.
    """

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)

    class Meta:
        unique_together = ["author", "name"]

    def get_absolute_url(self) -> str:
        return reverse("template-detail")

    @property
    def problem_count(self) -> int:
        return TemplateProblem.objects.filter(template=self).count()

    @property
    def problem_kinds(self) -> Iterable[ProblemKind]:
        entries = TemplateProblem.objects.filter(template=self)
        problem_kinds = [ProblemKind(entry.problem_kind) for entry in entries]
        return problem_kinds

    @property
    def problem_kind_labels(self) -> Iterable[str]:
        return [kind.label for kind in self.problem_kinds]

    def add_problem(self, kind: ProblemKind, count: int = 1):
        for __ in range(count):
            entry = TemplateProblem()
            entry.template = self
            entry.problem_kind = kind
            entry.save()

    def render(self) -> Pset | RenderError:
        problems = [ProblemKind(kind).generate() for kind in self.problem_kinds]
        latex = """
        \\documentclass{article}
        \\usepackage{amsfonts}
        \\begin{document}
        """
        for problem in problems:
            latex += f"\\textbf{{Definition}}: ${problem.definition}$\n\n"
            latex += f"\\textbf{{Solution}}: ${problem.solution}$\n\n"
        latex += "\\end{document}"

        with TemporaryDirectory() as tmp_dir:
            tex_file = f"{tmp_dir}/template.tex"
            pdf_file = f"{tmp_dir}/template.pdf"
            with open(tex_file, "w") as file:
                file.write(latex)

            try:
                run(["pdflatex", tex_file], cwd=tmp_dir, timeout=3)
            except TimeoutExpired:
                logger.error(f"pdflatex timed out for {self}")
                return RenderError()

            pset = Pset()
            pset.id = uuid.uuid4()
            pset.author = self.author
            pset.template = self
            pset.name = str(pset.id)
            with open(pdf_file, "rb") as file:
                pdf_file = File()
                pdf_file.data = file.read()
                pdf_file.save()
                pset.problems_pdf = pdf_file

        return pset

    def __str__(self) -> str:
        return self.name


class TemplateProblem(Entity):
    """
    A `ProblemKind` instance in the given `Template`.
    A single `ProblemKind` can be inserted 0, 1, or many times.
    """

    template = ForeignKey(Template, on_delete=CASCADE)
    problem_kind = IntegerField(choices=ProblemKind.choices)


class File(Entity):
    data = models.BinaryField()

    @property
    def as_base64(self) -> str:
        return base64.b64encode(self.data).decode("utf-8")


class Pset(Entity):
    """
    A problem set composed of documents rendered from a `Template`.
    """

    author = ForeignKey(User, on_delete=CASCADE)
    template = ForeignKey(Template, on_delete=CASCADE)
    name = models.CharField(max_length=255, validators=[MinLengthValidator(1)])
    is_saved = models.BooleanField(default=False)
    """
    Whether the test should be persisted.
    Any test that is not marked as saved is due for deletion.
    """
    problems_pdf = models.ForeignKey(File, on_delete=CASCADE, related_name="questions")

    class Meta:
        unique_together = ["author", "name"]

    @classmethod
    def delete_unsaved(cls, user: AbstractBaseUser | AnonymousUser):
        """
        Delete all unsaved tests.
        """
        Pset.objects.filter(is_saved=False, author=user).delete()
