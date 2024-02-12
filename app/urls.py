from django.urls import path

from app.views import (
    DashboardView,
    ProblemKindListView,
    PsetListView,
    TemplateDetailView,
    TemplateListView,
    generate_pset,
    pset_generation,
    save_pset,
)

app_name = "app"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("templates/", TemplateListView.as_view(), name="template-list"),
    path(
        "templates/<uuid:pk>/",
        TemplateDetailView.as_view(),
        name="template-detail",
    ),
    path("problem-kinds/", ProblemKindListView.as_view(), name="problemkind-list"),
    path("problem-sets/", PsetListView.as_view(), name="pset-list"),
    path(
        "problem-set-generation/<uuid:preview_pset_id>",
        pset_generation,
        name="pset-generation",
    ),
    path(
        "problem-set-generation/",
        pset_generation,
        name="pset-generation",
    ),
    path("generate-problem-set/", generate_pset, name="generate-pset"),
    path("save-problem-set/<uuid:pset_id>", save_pset, name="save-pset"),
]
