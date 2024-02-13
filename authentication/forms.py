from allauth.account.forms import LoginForm, SignupForm
from django.utils.translation import gettext_lazy as _


class AbiopetajaLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        self.remove_forgot_password_link()
        self.provide_translations()

    def provide_translations(self):
        """
        These fields are not translated in the allauth package as of 2024-02-13.
        """
        username_field = self.fields["login"]
        username_field.label = _("Username")

    def remove_forgot_password_link(self):
        password_field = self.fields["password"]
        password_field.help_text = ""


class AbiopetajaSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        self.provide_translations()
        self.remove_password_help_text()

    def provide_translations(self):
        """
        These fields are not translated in the allauth package as of 2024-02-13.
        """
        username_field = self.fields["username"]
        username_field.label = _("Username")

        email_field = self.fields["email"]
        email_field.label = _("Email (optional)")

    def remove_password_help_text(self):
        password_field = self.fields["password1"]
        password_field.help_text = ""
