from django.urls import path

from .html_views import (
    CitizenCareerView,
    CitizenCareerPDFView,
    AgentCareerView,
    AgentCareerPDFView,
)

urlpatterns = [
    # Citizen
    path(
        "portal/citizen/career/",
        CitizenCareerView.as_view(),
        name="citizen-career",
    ),
    path(
        "portal/citizen/career/pdf/",
        CitizenCareerPDFView.as_view(),
        name="citizen-career-pdf",
    ),
    # Agent
    path(
        "portal/agent/career/<int:affiliate_pk>/",
        AgentCareerView.as_view(),
        name="agent-career",
    ),
    path(
        "portal/agent/career/<int:affiliate_pk>/pdf/",
        AgentCareerPDFView.as_view(),
        name="agent-career-pdf",
    ),
]
