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
from app.forms import GenerateProblemSetForm, SaveProblemSetForm
from app.models import ProblemKind, ProblemSet, RenderError, Template

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "app/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            user=self.request.user,
            template_count=Template.objects.filter(author=self.request.user).count(),
            problemkind_count=len(ProblemKind.values),
            problem_set_count=ProblemSet.objects.filter(
                author=self.request.user, is_saved=True
            ).count(),
        )
        return context


@login_required
def problem_set_generation(
    request: HttpRequest, preview_problem_set_id: UUID | None = None
) -> HttpResponse:
    preview_problem_set = get_object_or_None(
        ProblemSet, id=preview_problem_set_id, author=request.user
    )
    disable_save_form = preview_problem_set is None or preview_problem_set.is_saved
    context = {
        "templates": Template.objects.filter(author=request.user),
        "generate_form": GenerateProblemSetForm(user=request.user),
        "save_form": SaveProblemSetForm(user=request.user),
        "preview_problem_set": preview_problem_set,
        "disable_save_form": disable_save_form,
    }
    return render(request, "app/problemset_generation.html", context)


@login_required
def generate_problem_set(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        ProblemSet.delete_unsaved(request.user)

        form = GenerateProblemSetForm(request.POST, user=request.user)
        if form.is_valid():
            template: Template = form.cleaned_data["template"]
            match template.render():
                case ProblemSet() as problem_set:
                    problem_set.save()
                    return redirect(
                        "app:problemset-generation",
                        preview_problem_set_id=problem_set.id,
                    )
                case RenderError():
                    messages.error(
                        request,
                        "Something went wrong and we weren't able to generate the problem set. Sorry!",
                    )
    return problem_set_generation(request)


@login_required
def save_problem_set(request: HttpRequest, problem_set_id: UUID) -> HttpResponse:
    problem_set = get_object_or_404(ProblemSet, id=problem_set_id, author=request.user)

    form = SaveProblemSetForm(request.POST, user=request.user)
    if form.is_valid():
        if problem_set.is_saved:
            messages.info(request, _("This problem set has already been saved"))
        else:
            problem_set.name = form.cleaned_data["name"]
            problem_set.is_saved = True
            problem_set.save()
            messages.success(request, _("The problem set was saved successfully"))
        return redirect("app:problemset-generation", preview_problem_set_id=problem_set_id)
    else:
        return problem_set_generation(request, problem_set_id)


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


class ProblemSetListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return ProblemSet.objects.filter(author=self.request.user, is_saved=True)


class ProblemSetDetailView(LoginRequiredMixin, DetailView):
    def get_queryset(self):
        return ProblemSet.objects.filter(author=self.request.user)
