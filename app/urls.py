from django.urls import path

from app.views import (
    DashboardView,
    ProblemKindListView,
    TemplateDetailView,
    TemplateListView,
    TestDetailView,
    TestListView,
    generate_test,
    save_test,
    test_generation,
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
    path("tests/", TestListView.as_view(), name="test-list"),
    path(
        "test-generation/<uuid:preview_test_id>",
        test_generation,
        name="test-generation",
    ),
    path(
        "test-generation/",
        test_generation,
        name="test-generation",
    ),
    path("test/<uuid:pk>/", TestDetailView.as_view(), name="test-detail"),
    path("generate-problem-set/", generate_test, name="generate-test"),
    path("save-test/<uuid:test_id>", save_test, name="save-test"),
]
