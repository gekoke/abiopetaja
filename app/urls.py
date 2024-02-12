from django.urls import path

from app.views import (
    ProblemKindListView,
    PsetListView,
    dashboard,
    generate_pset,
    pset_generation,
    save_pset,
    template_detail,
    template_list,
)

app_name = "app"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("templates/", template_list, name="template-list"),
    path("templates/<uuid:template_id>/", template_detail, name="template-detail"),
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
