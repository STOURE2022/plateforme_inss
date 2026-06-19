from django.urls import path
from . import html_views

# Note: app_name is NOT set here so that this urlconf can be included
# with two different namespaces (citizen_benefits and agent_benefits)
# from config/urls.py.

urlpatterns = [
    # Citizen URLs
    path("list/", html_views.CitizenBenefitListView.as_view(), name="citizen_benefit_list"),
    path("new/", html_views.CitizenBenefitCreateView.as_view(), name="citizen_benefit_create"),
    path("<int:pk>/", html_views.CitizenBenefitDetailView.as_view(), name="citizen_benefit_detail"),
    path("<int:pk>/submit/", html_views.CitizenBenefitSubmitView.as_view(), name="citizen_benefit_submit"),
    path("<int:pk>/documents/", html_views.CitizenBenefitDocumentUploadView.as_view(), name="citizen_benefit_docs"),

    # Agent URLs
    path("agent/list/", html_views.AgentBenefitListView.as_view(), name="agent_benefit_list"),
    path("agent/<int:pk>/", html_views.AgentBenefitDetailView.as_view(), name="agent_benefit_detail"),
    path("agent/<int:pk>/review/", html_views.AgentBenefitReviewView.as_view(), name="agent_benefit_review"),
]
