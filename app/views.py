import logging
from typing import Any, Iterable
from uuid import UUID

import django.views.generic
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import ContextMixin, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import DeleteView
from django.views.generic.list import ListView

from app.annoying import get_object_or_None
from app.errors import (
    EmptyTemplate,
    TestGenerationError,
)
from app.forms import (
    GenerateTestForm,
    SaveTestForm,
    TemplateCreateForm,
    TemplateProblemCreateFrom,
    TemplateProblemUpdateForm,
    TemplateUpdateForm,
    TestUpdateForm,
)
from app.models import (
    ProblemKind,
    Template,
    TemplateProblem,
    Test,
    TestVersion,
    UserFeedback,
)

logger = logging.getLogger(__name__)


class CancellationMixin(ContextMixin):
    cancellation_url = ""

    def get_cancellation_url(self):
        return self.cancellation_url

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["cancellation_url"] = self.get_cancellation_url()
        return context


class CreateView(django.views.generic.CreateView):
    template_name_suffix = "_create_form"


class UpdateView(django.views.generic.UpdateView):
    template_name_suffix = "_update_form"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "app/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            user=self.request.user,
            template_count=Template.objects.filter(author=self.request.user).count(),
            problemkind_count=len(ProblemKind.values),
            test_count=Test.objects.filter(author=self.request.user, is_saved=True).count(),
        )
        return context


@login_required
def test_generation(
    request: HttpRequest,
    preview_test_pk: UUID | None = None,
    save_test_form: SaveTestForm | None = None,
) -> HttpResponse:
    preview_test = get_object_or_None(Test, pk=preview_test_pk, author=request.user)
    generate_test_form = GenerateTestForm(user=request.user)
    show_save_form = preview_test is not None and not preview_test.is_saved
    save_test_form = (
        (save_test_form if save_test_form is not None else SaveTestForm(user=request.user))
        if show_save_form
        else None
    )

    context = {
        "preview_test": preview_test,
        "generate_test_form": generate_test_form,
        "save_test_form": save_test_form,
    }
    return render(request, "app/test_generation.html", context)


@login_required
def test_generate(request: HttpRequest) -> HttpResponse:
    def delete_unsaved_tests():
        Test.objects.filter(author=request.user, is_saved=False).delete()

    if request.method == "POST":
        form = GenerateTestForm(request.POST, user=request.user)
        if form.is_valid():
            delete_unsaved_tests()
            template = form.get_template()
            test_generation_parameters = form.get_test_generation_parameters()
            test = template.generate_test(test_generation_parameters)

            match test:
                case Test():
                    return redirect("app:test-generation", preview_test_pk=test.pk)
                case TestGenerationError(reason=EmptyTemplate()):
                    messages.error(
                        request,
                        _("This template has no problems and would result in an empty test."),
                    )
                    return redirect(request.path)

    return test_generation(request)


@login_required
def test_save(request: HttpRequest, pk: UUID) -> HttpResponse:
    test = get_object_or_404(Test, pk=pk, author=request.user)
    form = SaveTestForm(request.POST, user=request.user)

    if form.is_valid():
        test.name = form.cleaned_data["name"]
        test.is_saved = True
        test.save()
        message = _(
            '<div>The test was saved successfully. <a href="%(url)s">Click here</a> to view the test.</div>'
        ) % {"url": test.get_absolute_url()}
        messages.success(request, mark_safe(message))
        return redirect("app:test-generation", preview_test_pk=pk)
    return test_generation(request, pk, form)


@login_required
def testversion_download(request: HttpRequest, pk: UUID):
    if request.method != "GET":
        return HttpResponseNotAllowed(permitted_methods=["POST"])

    test_version = get_object_or_404(TestVersion, pk=pk, test__author=request.user)
    return HttpResponse(test_version.pdf.read(), content_type="application/pdf")


@login_required
def test_download(request: HttpRequest, pk: UUID):
    if request.method == "GET":
        test = get_object_or_404(Test, pk=pk, author=request.user)
        answer_key = test.answer_key_pdf
        return HttpResponse(answer_key.read(), content_type="application/pdf")

    return redirect("app:test-detail", kwargs={"pk": pk})


class ProblemKindListView(LoginRequiredMixin, ListView):
    template_name = "app/problemkind_list.html"

    def get_queryset(self) -> Iterable[ProblemKind]:  # pyright: ignore
        # get_queryset may return any iterable according to Django docs,
        # despite the type hint of the superclass implementation
        return list(ProblemKind)  # type: ignore

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["examples"] = [kind.generate() for kind in self.get_queryset()]
        return context


class TemplateListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return Template.objects.filter(author=self.request.user)


class TemplateDetailView(LoginRequiredMixin, DetailView):
    def get_queryset(self):
        return Template.objects.filter(author=self.request.user)


class TemplateCreateView(LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, CreateView):
    success_message = _("The template was created successfully.")
    success_url = reverse_lazy("app:template-list")
    cancellation_url = success_url

    model = Template
    form_class = TemplateCreateForm

    def form_valid(self, form):
        form.instance.author = self.request.user  # pyright: ignore
        return super().form_valid(form)


class TemplateUpdateView(LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, UpdateView):
    form_class = TemplateUpdateForm

    success_message = _("The template was updated successfully.")

    def get_success_url(self) -> str:
        return reverse_lazy("app:template-detail", kwargs={"pk": self.get_object().pk})

    def get_cancellation_url(self):
        return self.get_success_url()

    def get_queryset(self):
        return Template.objects.filter(author=self.request.user)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TemplateDeleteView(LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, DeleteView):
    success_url = reverse_lazy("app:template-list")
    success_message = _("The template was deleted successfully.")
    cancellation_url = success_url

    def get_cancellation_url(self):
        return reverse_lazy("app:template-detail", kwargs={"pk": self.get_object().pk})

    def get_queryset(self):
        return Template.objects.filter(author=self.request.user)


class TestListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user, is_saved=True)


class TestDetailView(LoginRequiredMixin, DetailView):
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)


class TestUpdateView(LoginRequiredMixin, UpdateView):
    success_url = reverse_lazy("app:test-list")
    success_message = _("The test was updated successfully.")

    form_class = TestUpdateForm

    def get_cancellation_url(self):
        return reverse_lazy("app:test-detail", kwargs={"pk": self.get_object().pk})

    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class TemplateProblemCreateView(
    LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, CreateView
):
    form_class = TemplateProblemCreateFrom

    model = TemplateProblem

    def get_template(self) -> Template:
        return get_object_or_404(Template, pk=self.kwargs["template_pk"])

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["template"] = self.get_template()
        return kwargs

    def get_success_url(self) -> str:
        return reverse_lazy("app:template-detail", kwargs={"pk": self.get_template().pk})

    def get_cancellation_url(self):
        return self.get_success_url()

    def form_valid(self, form):
        form.instance.template = self.get_template()  # type: ignore
        return super().form_valid(form)

    def get_queryset(self):
        return TemplateProblem.objects.filter(template__author=self.request.user)


class TemplateProblemUpdateView(
    LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, UpdateView
):
    form_class = TemplateProblemUpdateForm

    success_message = _("The problem entry was updated successfully.")

    def get_success_url(self) -> str:
        template_problem: TemplateProblem = self.get_object()  # type: ignore
        return reverse_lazy("app:template-detail", kwargs={"pk": template_problem.template.pk})

    def get_cancellation_url(self):
        return self.get_success_url()

    def get_queryset(self):
        return TemplateProblem.objects.filter(template__author=self.request.user)


class TemplateProblemDeleteView(
    LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, DeleteView
):
    success_message = _("The problem entry was deleted successfully.")

    def get_success_url(self) -> str:
        template_problem: TemplateProblem = self.get_object()  # type: ignore
        return reverse_lazy("app:template-detail", kwargs={"pk": template_problem.template.pk})

    def get_cancellation_url(self):
        return self.get_success_url()

    def get_queryset(self):
        return TemplateProblem.objects.filter(template__author=self.request.user)


class TestDeleteView(LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, DeleteView):
    success_url = reverse_lazy("app:test-list")
    success_message = _("The test was deleted successfully.")

    def get_cancellation_url(self):
        return reverse_lazy("app:test-detail", kwargs={"pk": self.get_object().pk})

    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)


class UserFeedbackCreateView(
    LoginRequiredMixin, CancellationMixin, SuccessMessageMixin, CreateView
):
    model = UserFeedback
    fields = ["content"]

    success_url = reverse_lazy("app:dashboard")
    success_message = _("Your feedback was submitted. Thanks!")

    cancellation_url = success_url

    def form_valid(self, form):
        form.instance.author = self.request.user  # pyright: ignore
        return super().form_valid(form)
