from django.urls import path

from app.views import (
    DashboardView,
    ProblemKindListView,
    ProblemSetDetailView,
    ProblemSetListView,
    TemplateDetailView,
    TemplateListView,
    generate_problem_set,
    problem_set_generation,
    save_problem_set,
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
    path("problem-sets/", ProblemSetListView.as_view(), name="problemset-list"),
    path(
        "problem-set-generation/<uuid:preview_problem_set_id>",
        problem_set_generation,
        name="problemset-generation",
    ),
    path(
        "problem-set-generation/",
        problem_set_generation,
        name="problemset-generation",
    ),
    path("problem-set/<uuid:pk>/", ProblemSetDetailView.as_view(), name="problemset-detail"),
    path("generate-problem-set/", generate_problem_set, name="generate-problemset"),
    path("save-problem-set/<uuid:problem_set_id>", save_problem_set, name="save-problemset"),
]
