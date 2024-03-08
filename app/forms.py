from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.forms import Form, IntegerField, ModelChoiceField, ModelForm, ValidationError
from django.forms.widgets import TextInput
from django.utils.translation import gettext_lazy as _

from app.models import Template, TemplateProblem, Test, TestGenerationParameters


class GenerateTestForm(Form):
    template = ModelChoiceField(
        queryset=None,
        label=_("Template to generate test from"),
        empty_label=None,
    )

    test_version_count = IntegerField(
        min_value=1, max_value=6, initial=1, label=_("Number of test versions")
    )

    def __init__(self, *args, user: AbstractBaseUser | AnonymousUser, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self.fields["template"].queryset = Template.objects.filter(author=user)

    def get_template(self) -> Template:
        assert self.is_valid()
        return self.cleaned_data["template"]

    def get_test_generation_parameters(self) -> TestGenerationParameters:
        assert self.is_valid()
        return TestGenerationParameters(test_version_count=self.cleaned_data["test_version_count"])


class SaveTestForm(ModelForm):
    def __init__(self, *args, user: AbstractBaseUser | AnonymousUser, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self.user = user

    class Meta:
        model = Test
        fields = ["name"]
        hidden_fields = ["id"]
        labels = {
            "name": _("Name"),
        }
        widgets = {
            "name": TextInput(attrs={"placeholder": _("My Test")}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Test.objects.filter(name=name, author=self.user).exists():
            raise ValidationError(_("A problem set with this name already exists"), code="exists")

        return name


class TemplateProblemUpdateForm(ModelForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    count = IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        label=_("Number of occurences"),
    )

    class Meta:
        model = TemplateProblem
        fields = ["count"]
