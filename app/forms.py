import logging

from django import forms
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser, User
from django.db.models import Q
from django.forms import (
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    Textarea,
    ValidationError,
)
from app.topics import get_all_topic_choices
from django.forms.widgets import TextInput
from django.utils.translation import gettext_lazy as _

# Import only the models that are still used.
from app.models import Template, TemplateProblem, Test, TestGenerationParameters

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


class TestUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user: AbstractBaseUser | AnonymousUser = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    class Meta:
        model = Test
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Test.objects.filter(~Q(pk=self.instance.pk), name=name, author=self.user).exists():
            raise ValidationError(_("Another test with this name already exists"), code="exists")
        return name


class TemplateCreateForm(ModelForm):
    class Meta:
        model = Template
        exclude = ["author"]
        widgets = {
            "name": TextInput(attrs={"placeholder": _("Inequalities")}),
            "title": Textarea(attrs={"placeholder": _("Inequalities Test, Spring 2024")}),
        }


class TemplateUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user: AbstractBaseUser | AnonymousUser = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    class Meta:
        model = Template
        exclude = ["author"]

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Template.objects.filter(~Q(pk=self.instance.pk), name=name, author=self.user).exists():
            raise ValidationError(
                _("Another template with this name already exists"), code="exists"
            )
        return name


TEMPLATE_PROBLEM_COUNT_FIELD = IntegerField(
    min_value=1,
    max_value=20,
    initial=1,
    label=_("Number of occurrences"),
)


class TemplateProblemCreateForm(ModelForm):
    count = TEMPLATE_PROBLEM_COUNT_FIELD
    topic = forms.ChoiceField(choices= get_all_topic_choices(), label=_("topic"))
    def __init__(self, *args, **kwargs) -> None:
        self.user: User = kwargs.pop("user")
        self.template: Template = kwargs.pop("template")
        super().__init__(*args, **kwargs)
        self.fields["topic"].initial = "AVALDISED"

    class Meta:
        model = TemplateProblem
        fields = ["topic", "difficulty", "count"]

    def clean_topic(self):
        topic = self.cleaned_data.get("topic", "")
        if topic == "":
            raise ValidationError(_("Topic cannot be empty"))
        return topic

    def clean(self):
        cleaned_data = super().clean()
        topic = cleaned_data.get("topic")
        difficulty = cleaned_data.get("difficulty")

        if topic and difficulty:
            # Check for existing TemplateProblem with same topic & difficulty
            exists = TemplateProblem.objects.filter(
                template=self.template,
                topic=topic,
                difficulty=difficulty
            ).exists()
            if exists:
                raise ValidationError(
                    _("This template already contains a problem for this topic and difficulty"),
                    code="exists"
                )

        return cleaned_data

class TemplateProblemUpdateForm(ModelForm):
    count = TEMPLATE_PROBLEM_COUNT_FIELD

    class Meta:
        model = TemplateProblem
        fields = ["count"]


DIFFICULTY_CHOICES = [
    ("A", "Easy"),
    ("B", "Medium"),
    ("C", "Hard"),
]


class AITestGenerationForm(forms.Form):
    topic = forms.CharField(
        label="Topic",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "e.g., Trigonometry"}),
        required=True,
    )
    difficulty = forms.ChoiceField(
        label="Difficulty",
        choices=DIFFICULTY_CHOICES,
        required=True,
    )
    number_of_problems = forms.IntegerField(
        label="Number of Problems",
        min_value=1,
        max_value=20,
        initial=5,
        required=True,
    )
