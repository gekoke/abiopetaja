from django.urls import path

from app.views import (
    DashboardView,
    ProblemKindListView,
    TemplateDetailView,
    TemplateListView,
    TestDetailView,
    TestListView,
    test_generate,
    test_generation,
    test_save,
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
    path("tests/<uuid:pk>/", TestDetailView.as_view(), name="test-detail"),
    path("test-generate/", test_generate, name="test-generate"),
    path("tests/<uuid:test_id>/save", test_save, name="test-save"),
]
