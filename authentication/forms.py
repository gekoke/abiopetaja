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

        self.remove_password_help_text()

    def remove_password_help_text(self):
        password_field = self.fields["password1"]
        password_field.help_text = ""
