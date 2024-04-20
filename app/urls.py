from django.urls import path

from app.views import (
    DashboardView,
    ProblemKindListView,
    TemplateCreateView,
    TemplateDeleteView,
    TemplateDetailView,
    TemplateListView,
    TemplateProblemCreateView,
    TemplateProblemDeleteView,
    TemplateProblemUpdateView,
    TemplateUpdateView,
    TestDeleteView,
    TestDetailView,
    TestListView,
    test_generate,
    test_generation,
    test_save,
    testversion_download,
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
    path(
        "templates/create",
        TemplateCreateView.as_view(),
        name="template-create",
    ),
    path(
        "templates/<uuid:pk>/update",
        TemplateUpdateView.as_view(),
        name="template-update",
    ),
    path(
        "templates/<uuid:pk>/delete",
        TemplateDeleteView.as_view(),
        name="template-delete",
    ),
    path(
        "template-problems/create/<uuid:template_pk>",
        TemplateProblemCreateView.as_view(),
        name="templateproblem-create",
    ),
    path(
        "template-problems/<uuid:pk>/update",
        TemplateProblemUpdateView.as_view(),
        name="templateproblem-update",
    ),
    path(
        "template-problems/<uuid:pk>/delete",
        TemplateProblemDeleteView.as_view(),
        name="templateproblem-delete",
    ),
    path("problem-kinds/", ProblemKindListView.as_view(), name="problemkind-list"),
    path(
        "test-generation/<uuid:preview_test_pk>",
        test_generation,
        name="test-generation",
    ),
    path(
        "test-generation/",
        test_generation,
        name="test-generation",
    ),
    path("tests/", TestListView.as_view(), name="test-list"),
    path("tests/<uuid:pk>/", TestDetailView.as_view(), name="test-detail"),
    path("test-generate/", test_generate, name="test-generate"),
    path("tests/<uuid:pk>/delete", TestDeleteView.as_view(), name="test-delete"),
    path("tests/<uuid:pk>/save", test_save, name="test-save"),
    path("test-versions/<uuid:pk>/download", testversion_download, name="testversion-download"),
]
