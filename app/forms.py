from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.forms import Form, ModelChoiceField, ModelForm, ValidationError
from django.forms.widgets import TextInput
from django.utils.translation import gettext_lazy as _

from app.models import Pset, Template


class GeneratePsetForm(Form):
    template = ModelChoiceField(
        queryset=None,
        label=_("Choose a template to generate a problem set from"),
        empty_label=None,
    )

    def __init__(self, *args, user: AbstractBaseUser | AnonymousUser, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self.fields["template"].queryset = Template.objects.filter(author=user)


class SavePsetForm(ModelForm):
    def __init__(self, *args, user: AbstractBaseUser | AnonymousUser, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self.user = user

    class Meta:
        model = Pset
        fields = ["name"]
        hidden_fields = ["id"]
        labels = {
            "name": _("Name"),
        }
        widgets = {
            "name": TextInput(attrs={"placeholder": _("My Problem Set")}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Pset.objects.filter(name=name, author=self.user).exists():
            raise ValidationError(
                _("A problem set with this name already exists"), code="exists"
            )

        return name
