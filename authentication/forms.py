from allauth.account.forms import LoginForm, SignupForm


class AbiopetajaLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        self.remove_forgot_password_link()

    def remove_forgot_password_link(self):
        password_field = self.fields["password"]
        password_field.help_text = ""


class AbiopetajaSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

        self.hide_email_fields()
        self.remove_password_help_text()

    def hide_email_fields(self):
        """
        Hide email fields, as we don't use them for anything.

        Note that we don't *remove* them, as that would
        result in `NOT NULL constraint failed: auth_user.email`.
        """
        if "email" in self.fields:
            self.fields["email"].widget = self.fields["email"].hidden_widget()
        if "email2" in self.fields:
            self.fields["email2"].widget = self.fields["email2"].hidden_widget()

    def remove_password_help_text(self):
        password_field = self.fields["password1"]
        password_field.help_text = ""
