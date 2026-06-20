from django.urls import path

from . import html_views

urlpatterns = [
    # -----------------------------------------------------------------------
    # Employer
    # -----------------------------------------------------------------------
    path(
        "portal/employer/declarations/",
        html_views.EmployerDeclarationListView.as_view(),
        name="employer-declaration-list",
    ),
    path(
        "portal/employer/declarations/new/",
        html_views.EmployerDeclarationCreateView.as_view(),
        name="employer-declaration-create",
    ),
    path(
        "portal/employer/declarations/lookup/",
        html_views.AffiliateLookupView.as_view(),
        name="affiliate-lookup",
    ),
    path(
        "portal/employer/declarations/<int:pk>/",
        html_views.EmployerDeclarationDetailView.as_view(),
        name="employer-declaration-detail",
    ),
    path(
        "portal/employer/declarations/<int:pk>/add-line/",
        html_views.EmployerDeclarationAddLineView.as_view(),
        name="employer-declaration-add-line",
    ),
    path(
        "portal/employer/declarations/<int:pk>/remove-line/<int:line_pk>/",
        html_views.EmployerDeclarationRemoveLineView.as_view(),
        name="employer-declaration-remove-line",
    ),
    path(
        "portal/employer/declarations/<int:pk>/submit/",
        html_views.EmployerDeclarationSubmitView.as_view(),
        name="employer-declaration-submit",
    ),
    path(
        "portal/employer/declarations/<int:pk>/reopen/",
        html_views.EmployerDeclarationReopenView.as_view(),
        name="employer-declaration-reopen",
    ),
    path(
        "portal/employer/declarations/<int:pk>/bulletin/",
        html_views.EmployerDeclarationBulletinView.as_view(),
        name="employer-declaration-bulletin",
    ),
    # -----------------------------------------------------------------------
    # Agent
    # -----------------------------------------------------------------------
    path(
        "portal/agent/declarations/",
        html_views.AgentDeclarationListView.as_view(),
        name="agent-declaration-list",
    ),
    path(
        "portal/agent/declarations/<int:pk>/",
        html_views.AgentDeclarationDetailView.as_view(),
        name="agent-declaration-detail",
    ),
    path(
        "portal/agent/declarations/<int:pk>/validate/",
        html_views.AgentDeclarationValidateView.as_view(),
        name="agent-declaration-validate",
    ),
    path(
        "portal/agent/declarations/<int:pk>/reject/",
        html_views.AgentDeclarationRejectView.as_view(),
        name="agent-declaration-reject",
    ),
]
