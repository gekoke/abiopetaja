import logging
from typing import Any, Iterable
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import (
    CreateView,
    DeleteView,
    UpdateView,
)
from django.views.generic.list import ListView

from app.annoying import get_object_or_None
from app.forms import (
    GenerateTestForm,
    SaveTestForm,
    TemplateCreateForm,
    TemplateProblemCreateFrom,
    TemplateProblemUpdateForm,
    TemplateUpdateForm,
)
from app.models import (
    FailedUnexpectedly,
    File,
    ProblemKind,
    RenderError,
    Template,
    TemplateProblem,
    Test,
    TestVersion,
    Timeout,
)

logger = logging.getLogger(__name__)


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
    request: HttpRequest, preview_test_pk: UUID | None = None, save_form: SaveTestForm | None = None
) -> HttpResponse:
    preview_test = get_object_or_None(Test, pk=preview_test_pk, author=request.user)
    test_version = preview_test.testversion_set.first() if preview_test is not None else None
    render_result = None if test_version is None else test_version.render()
    preview_pdf_b64_data = None

    if render_result is not None:
        match render_result:
            case File() as file:
                preview_pdf_b64_data = file.as_base64()
            case RenderError(reason=FailedUnexpectedly()):
                messages.error(request, _("Something went wrong on our end. Sorry!"))
            case RenderError(reason=Timeout()):
                messages.error(request, _("Rendering the test took too long. Sorry!"))

    context = {
        "templates": Template.objects.filter(author=request.user),
        "generate_form": GenerateTestForm(user=request.user),
        "save_form": save_form if save_form is not None else SaveTestForm(user=request.user),
        "preview_test": preview_test,
        "show_save_form": preview_test is not None and not preview_test.is_saved,
        "preview_pdf_b64_data": preview_pdf_b64_data,
    }
    return render(request, "app/test_generation.html", context)


@login_required
def test_generate(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = GenerateTestForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.get_template()
            test_generation_parameters = form.get_test_generation_parameters()

            test = template.generate_test(test_generation_parameters)
            return redirect("app:test-generation", preview_test_pk=test.pk)

    return test_generation(request)


@login_required
def test_save(request: HttpRequest, pk: UUID) -> HttpResponse:
    test = get_object_or_404(Test, pk=pk, author=request.user)

    form = SaveTestForm(request.POST, user=request.user)
    if form.is_valid():
        if test.is_saved:
            messages.info(request, _("This test has already been saved."))
        else:
            test.name = form.cleaned_data["name"]
            test.is_saved = True
            test.save()
            messages.success(request, _("The test was saved successfully."))
        return redirect("app:test-generation", preview_test_pk=pk)
    else:
        return test_generation(request, pk, form)


@login_required
def testversion_download(request: HttpRequest, pk: UUID):
    if request.method == "GET":
        test_version = get_object_or_404(TestVersion, pk=pk, test__author=request.user)
        render_result = test_version.render()
        match render_result:
            case File() as file:
                return HttpResponse(bytes(file.data), content_type="application/pdf")
            case RenderError(reason=FailedUnexpectedly()):
                messages.error(request, _("Something went wrong on our end. Sorry!"))
            case RenderError(reason=Timeout()):
                messages.error(request, _("Rendering the test took too long. Sorry!"))

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


class TemplateCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    success_message = _("The template was created successfully.")
    success_url = reverse_lazy("app:template-list")

    model = Template
    form_class = TemplateCreateForm
    template_name_suffix = "_create_form"

    def form_valid(self, form):
        form.instance.author = self.request.user  # pyright: ignore
        return super().form_valid(form)


class TemplateUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    template_name_suffix = "_update_form"
    form_class = TemplateUpdateForm

    success_message = _("The template was updated successfully.")

    def get_success_url(self) -> str:
        return reverse_lazy("app:template-detail", kwargs={"pk": self.get_object().pk})  # type: ignore

    def get_queryset(self):
        return Template.objects.filter(author=self.request.user)


class TemplateDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    success_url = reverse_lazy("app:template-list")
    success_message = _("The template was deleted successfully.")

    def get_queryset(self):
        return Template.objects.filter(author=self.request.user)


class TestListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user, is_saved=True)


class TestDetailView(LoginRequiredMixin, DetailView):
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)


class TemplateProblemCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    template_name_suffix = "_create_form"
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

    def form_valid(self, form):
        form.instance.template = self.get_template()  # type: ignore
        return super().form_valid(form)

    def get_queryset(self):
        return TemplateProblem.objects.filter(template__author=self.request.user)


class TemplateProblemUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    template_name_suffix = "_update_form"
    form_class = TemplateProblemUpdateForm

    success_message = _("The problem entry was updated successfully.")

    def get_success_url(self) -> str:
        return reverse_lazy("app:template-detail", kwargs={"pk": self.get_object().template.pk})  # type: ignore

    def get_queryset(self):
        return TemplateProblem.objects.filter(template__author=self.request.user)


class TemplateProblemDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    success_message = _("The problem entry was deleted successfully.")

    def get_success_url(self) -> str:
        return reverse_lazy("app:template-detail", kwargs={"pk": self.get_object().template.pk})  # type: ignore

    def get_queryset(self):
        return TemplateProblem.objects.filter(template__author=self.request.user)


class TestDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    success_url = reverse_lazy("app:test-list")
    success_message = _("The test was deleted successfully.")

    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)
