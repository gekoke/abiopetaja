from __future__ import annotations
from collections import defaultdict
import logging
import uuid

from collections import Counter
from base64 import b64encode
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import (
    CASCADE,
    CheckConstraint,
    ForeignKey,
    Model,
    PositiveIntegerField,
    Q,
    JSONField,
    TextField,
)
from django.utils import translation
import json
from app.topics import get_all_topic_choices
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db.models.constraints import UniqueConstraint
from django.urls import reverse
from django.utils.translation import gettext, pgettext_lazy, get_language
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel, Field
from typing import Iterable
from typing_extensions import TYPE_CHECKING

from app.latex import render_answer_key, render_test_version
from app.pdf import PDF, PDFCompilationError, compile_pdf

logger = logging.getLogger(__name__)


def get_short_lang() -> str:
    """
    Return 'et' if the current active language starts with 'et',
    otherwise return 'en'.
    """
    lang = get_language() or "et"
    return "et" if lang.startswith("et") else "en"


class Entity(Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TestGenerationParameters(BaseModel):
    test_version_count: int = Field(default=1, ge=1, le=6)


type TestGenerationError = "EmptyTemplate | PDFCompilationError"


class EmptyTemplate:
    pass


class Template(Entity):
    """A template is a collection of problem selection entries (TemplateProblem)
    that are later rendered into a Test.
    """

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
    def problem_kinds(self) -> Iterable[str]:
        # Now each TemplateProblem has a topic and difficulty.
        return [
            f"{entry.topic} ({entry.get_difficulty_display()})"
            for entry in self.templateproblem_set.all()
        ]

    @transaction.atomic
    def add_problem(self, topic: str, difficulty: str, count: int = 1):
        entry = TemplateProblem()
        entry.template = self
        entry.topic = topic
        entry.difficulty = difficulty
        entry.count = count
        entry.save()


    
    def generate_test(self, params: TestGenerationParameters) -> Test | TestGenerationError:
        # 1) Create the Test shell
        test = Test.objects.create(author=self.author, is_saved=False, title=self.title)

        if not self.problem_count:
            return EmptyTemplate()

        # 2) Pre-create stub versions
        version_ids = [
            TestVersion.objects.create(test=test, version_number=v).id
            for v in range(1, params.test_version_count + 1)
        ]
        current_lang = translation.get_language() or "et"
        # ───────────────────────── version worker ─────────────────────────
        def _populate_version(tv_id: int, lang: str) -> TestVersion:
            tv = TestVersion.objects.get(id=tv_id)
            translation.activate(lang)
            # ------------------------------------------------------------------
            # A. collect quotas per topic/difficulty for this template
            # ------------------------------------------------------------------
            quotas: dict[str, dict[str, int]] = defaultdict(lambda: {"A": 0, "B": 0, "C": 0})
            for row in self.templateproblem_set.all():
                quotas[row.topic][row.difficulty] += row.count

            # ------------------------------------------------------------------
            # B. generate AI batches per topic *concurrently*
            # ------------------------------------------------------------------
            from app.math import generate_mixed_difficulty_problems

            ai_batches: dict[str, list[dict]] = {}  # topic -> list[problem]
            
            with ThreadPoolExecutor(max_workers=min(8, len(quotas))) as pool:
                fut_map = {
                    pool.submit(
                        generate_mixed_difficulty_problems,
                        topic=topic,
                        lang=lang,
                        counts = {d: c + 1 for d, c in diff.items() if c > 0},  # +1 slack
                    ): topic
                        
                    for topic, diff in quotas.items()
                }
                for fut in as_completed(fut_map):
                    topic = fut_map[fut]
                    try:
                        ai_batches[topic] = fut.result()
                    except Exception as exc:
                        logger.error("AI generation failed for topic %s: %s", topic, exc)
                        ai_batches[topic] = []

            # ------------------------------------------------------------------
            # C. write problems back respecting quotas
            # ------------------------------------------------------------------
            accepted: dict[tuple[str, str], int] = defaultdict(int)  # (topic, diff) -> count
            for topic, batch in ai_batches.items():
                for obj in batch:
                    diff = obj["difficulty"]
                    key = (topic, diff)
                    if accepted[key] >= quotas[topic][diff]:
                        continue
                    TestVersionProblem.objects.create(
                        test_version=tv,
                        topic=topic,
                        difficulty=diff,
                        definition=obj["definition"],
                        solution=obj["solution"],
                        spec=obj["spec"],
                    )
                    accepted[key] += 1

            # ------------------------------------------------------------------
            # D. build PDF (retry loop unchanged)
            # ------------------------------------------------------------------
            while True:
                pdf_result = tv.generate_pdf()
                if isinstance(pdf_result, PDF):
                    tv.pdf.save(f"{tv.id}.pdf", ContentFile(pdf_result.data))
                    break
                bad = tv.testversionproblem_set.order_by("-created_at").first()
                if not bad:
                    break
                bad.delete()

            tv.save()
            return tv

        # 3) populate versions in parallel
        populated: list[TestVersion] = []
        with ThreadPoolExecutor(max_workers=len(version_ids)) as vexec:
            futures = [vexec.submit(_populate_version, vid, current_lang) for vid in version_ids]
            populated = [f.result() for f in as_completed(futures)]
            for f in as_completed(futures):
                populated.append(f.result())

        # 4) attach versions & build answer key
        for tv in populated:
            test.add_version(tv)

        ak = test.generate_answer_key_pdf()
        if isinstance(ak, PDF):
            test.answer_key_pdf.save(f"{test.id}.pdf", ContentFile(ak.data))
        else:
            return ak

        test.save()
        return test

        # ───────────────────────────────────────────────────────────────────


        

    @property
    def entries(self):
        return self.templateproblem_set.all()

    def __str__(self) -> str:
        return self.name


DIFFICULTY_CHOICES = [
    ("A", "Easy"),
    ("B", "Medium"),
    ("C", "Hard"),
]


class TemplateProblem(Entity):
    """
    A TemplateProblem now represents a chosen topic and difficulty for generating math problems.
    """

    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    topic = models.CharField(max_length=100, choices=get_all_topic_choices())
    
    difficulty = models.CharField(
        max_length=1,
        choices=DIFFICULTY_CHOICES,
        default="A",  # Default difficulty; change if needed
    )

    count = PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(20),
        ]
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["template", "topic", "difficulty"],
                name="unique_topic_difficulty_per_template",
            )
        ]

    def __str__(self):
        return f"{self.topic} - {self.get_difficulty_display()}"


class TestVersion(Entity):
    """A version of a Test."""

    if TYPE_CHECKING:
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

    def generate_pdf(self) -> "PDFCompilationError | PDF":
        return compile_pdf(render_test_version(self))

    def pdf_b64_str(self) -> str:
        return b64encode(self.pdf.read()).decode("utf-8")


class TestVersionProblem(Entity):
    topic = models.CharField(
        max_length=100,
        help_text=_("The topic of the problem (e.g., ARVUHULGAD, AVALDISED, etc.)"),
        default="AVALDISED",
    )
    difficulty = models.CharField(
        max_length=1,
        choices=[("A", _("Lihtne")), ("B", _("Keskmine")), ("C", _("Raske"))],
        help_text=_("The difficulty of the problem"),
        default="A",
    )
    definition = models.TextField()
    solution = models.TextField()
    test_version = models.ForeignKey(TestVersion, on_delete=CASCADE)
    spec = models.JSONField(null=True, blank=True)

    @property
    def problem_text(self) -> str:
        if self.topic:
            return f"{self.topic} ({self.get_difficulty_display()})"
        return _("Generated Problem")


class Test(Entity):
    """A test composed of rendered documents from a Template."""

    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager

        from app.pdf import PDFCompilationError

        testversion_set = RelatedManager["TestVersion"]()

    author = ForeignKey(User, on_delete=CASCADE)
    name = models.CharField(
        _("Name"),
        max_length=255,
        validators=[MinLengthValidator(1)],
        null=True,
    )
    is_saved = models.BooleanField(default=False)
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
    def versions(self) -> Iterable["TestVersion"]:
        return self.testversion_set.all()

    def get_absolute_url(self) -> str:
        return reverse("app:test-detail", kwargs={"pk": self.pk})

    def add_version(self, test_version: "TestVersion") -> None:
        self.testversion_set.add(test_version)

    def answer_key_pdf_b64_str(self) -> str:
        return b64encode(self.answer_key_pdf.read()).decode("utf-8")

    def generate_answer_key_pdf(self) -> "PDFCompilationError | PDF":
        return compile_pdf(render_answer_key(self))

    def __str__(self):
        return self.name if self.name is not None else gettext("[Unnamed Test]")


class UserFeedback(Entity):
    author = ForeignKey(User, on_delete=CASCADE)
    content = TextField(pgettext_lazy("of a user feedback", "Content"), blank=False)
