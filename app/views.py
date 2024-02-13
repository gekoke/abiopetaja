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
from app.forms import GeneratePsetForm, SavePsetForm
from app.models import ProblemKind, Pset, RenderError, Template

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "app/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            user=self.request.user,
            template_count=Template.objects.filter(author=self.request.user).count(),
            problemkind_count=len(ProblemKind.values),
            pset_count=Pset.objects.filter(author=self.request.user, is_saved=True).count(),
        )
        return context


@login_required
def pset_generation(request: HttpRequest, preview_pset_id: UUID | None = None) -> HttpResponse:
    preview_pset = get_object_or_None(Pset, id=preview_pset_id, author=request.user)
    disable_save_form = preview_pset is None or preview_pset.is_saved
    context = {
        "templates": Template.objects.filter(author=request.user),
        "generate_form": GeneratePsetForm(user=request.user),
        "save_form": SavePsetForm(user=request.user),
        "preview_pset": preview_pset,
        "disable_save_form": disable_save_form,
    }
    return render(request, "app/pset_generation.html", context)


@login_required
def generate_pset(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        Pset.delete_unsaved(request.user)

        form = GeneratePsetForm(request.POST, user=request.user)
        if form.is_valid():
            template: Template = form.cleaned_data["template"]
            match template.render():
                case Pset() as pset:
                    pset.save()
                    return redirect(
                        "app:pset-generation",
                        preview_pset_id=pset.id,
                    )
                case RenderError():
                    messages.error(
                        request,
                        "Something went wrong and we weren't able to generate the problem set. Sorry!",
                    )
    return pset_generation(request)


@login_required
def save_pset(request: HttpRequest, pset_id: UUID) -> HttpResponse:
    pset = get_object_or_404(Pset, id=pset_id, author=request.user)

    form = SavePsetForm(request.POST, user=request.user)
    if form.is_valid():
        if pset.is_saved:
            messages.info(request, _("This problem set has already been saved"))
        else:
            pset.name = form.cleaned_data["name"]
            pset.is_saved = True
            pset.save()
            messages.success(request, _("The problem set was saved successfully"))
        return redirect("app:pset-generation", preview_pset_id=pset_id)
    else:
        return pset_generation(request, pset_id)


class ProblemKindListView(LoginRequiredMixin, ListView):
    template_name = "app/problemkind_list.html"

    def get_queryset(self) -> list[ProblemKind]:
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


class PsetListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return Pset.objects.filter(author=self.request.user, is_saved=True)
