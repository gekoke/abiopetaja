import logging
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from app.annoying import get_object_or_None
from app.forms import GenerateTestForm, SaveTestForm
from app.models import File, ProblemKind, RenderError, Template, Test

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
def test_generation(request: HttpRequest, preview_test_id: UUID | None = None) -> HttpResponse:
    preview_test = get_object_or_None(Test, id=preview_test_id, author=request.user)
    test_version = preview_test.testversion_set.first() if preview_test is not None else None
    render_result = None if test_version is None else test_version.render()
    preview_pdf_b64_data = None

    if render_result is not None:
        match render_result:
            case File() as file:
                preview_pdf_b64_data = file.as_base64()
            case RenderError():
                messages.error(request, _("Something went wrong on our end. Sorry!"))

    context = {
        "templates": Template.objects.filter(author=request.user),
        "generate_form": GenerateTestForm(user=request.user),
        "save_form": SaveTestForm(user=request.user),
        "preview_test": preview_test,
        "show_save_form": preview_test is not None and not preview_test.is_saved,
        "preview_pdf_b64_data": preview_pdf_b64_data,
    }
    return render(request, "app/test_generation.html", context)


@login_required
def generate_test(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = GenerateTestForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.get_template()
            test_generation_parameters = form.get_test_generation_parameters()

            test = template.generate_test(test_generation_parameters)
            return redirect("app:test-generation", preview_test_id=test.id)

    return test_generation(request)


@login_required
def save_test(request: HttpRequest, test_id: UUID) -> HttpResponse:
    problem_set = get_object_or_404(Test, id=test_id, author=request.user)

    form = SaveTestForm(request.POST, user=request.user)
    if form.is_valid():
        if problem_set.is_saved:
            messages.info(request, _("This problem set has already been saved"))
        else:
            problem_set.name = form.cleaned_data["name"]
            problem_set.is_saved = True
            problem_set.save()
            messages.success(request, _("The test was saved successfully"))
        return redirect("app:test-generation", preview_test_id=test_id)
    else:
        return test_generation(request, test_id)


class ProblemKindListView(LoginRequiredMixin, ListView):
    template_name = "app/problemkind_list.html"

    def get_queryset(self) -> list[ProblemKind]:  # pyright: ignore
        # get_queryset may return any iterable
        return list(ProblemKind)

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


class TestListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user, is_saved=True)


class TestDetailView(LoginRequiredMixin, DetailView):
    def get_queryset(self):
        return Test.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        test: Test = self.get_object()  # type: ignore
        test_version = test.testversion_set.first()
        assert test_version is not None

        render_result = test_version.render()
        if type(render_result) is File:
            context["pdf_b64_data"] = render_result.as_base64()

        return context
