import logging

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.forms import (
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    ValidationError,
)
from django.forms.widgets import TextInput
from django.utils.translation import gettext_lazy as _

from app.models import ProblemKind, Template, TemplateProblem, Test, TestGenerationParameters

logger = logging.getLogger(__name__)


class GenerateTestForm(Form):
    template = ModelChoiceField(
        queryset=None,
        label=_("Template to generate test from"),
        empty_label=None,
    )

    test_version_count = IntegerField(
        min_value=1, max_value=6, initial=1, label=_("Number of test versions")
    )

    def __init__(self, *args, **kwargs):
        self.user: AbstractBaseUser | AnonymousUser = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self.fields["template"].queryset = Template.objects.filter(author=self.user)

    def get_template(self) -> Template:
        assert self.is_valid()
        return self.cleaned_data["template"]

    def get_test_generation_parameters(self) -> TestGenerationParameters:
        assert self.is_valid()
        return TestGenerationParameters(test_version_count=self.cleaned_data["test_version_count"])


class SaveTestForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user: AbstractBaseUser | AnonymousUser = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    class Meta:
        model = Test
        fields = ["name"]
        labels = {
            "name": _("Name"),
        }
        widgets = {
            "name": TextInput(attrs={"placeholder": _("My Test")}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Test.objects.filter(name=name, author=self.user).exists():
            raise ValidationError(_("A test with this name already exists"), code="exists")

        return name


class TemplateCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    class Meta:
        model = Template
        exclude = ["author"]
        labels = {
            "name": _("Name"),
        }
        widgets = {
            "name": TextInput(attrs={"placeholder": _("My Template")}),
        }


TEMPLATE_PROBLEM_COUNT_FIELD = IntegerField(
    min_value=1,
    max_value=20,
    initial=1,
    label=_("Number of occurences"),
)


class TemplateProblemCreateFrom(ModelForm):
    count = TEMPLATE_PROBLEM_COUNT_FIELD

    def __init__(self, *args, **kwargs) -> None:
        self.user: User = kwargs.pop("user")
        self.template: Template = kwargs.pop("template")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    class Meta:
        model = TemplateProblem
        fields = ["problem_kind", "count"]

    def clean_problem_kind(self):
        problem_kind: ProblemKind = self.cleaned_data["problem_kind"]
        template_already_has_problem_kind = problem_kind in self.template.problem_kinds
        if template_already_has_problem_kind:
            raise ValidationError(_("This template already contains this problem kind"))
        return problem_kind


class TemplateProblemUpdateForm(ModelForm):
    count = TEMPLATE_PROBLEM_COUNT_FIELD

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    class Meta:
        model = TemplateProblem
        fields = ["count"]
