from django.urls import path
from . import html_views

app_name = "agent_benefits"

urlpatterns = [
    path("list/", html_views.AgentBenefitListView.as_view(), name="agent_benefit_list"),
    path("<int:pk>/", html_views.AgentBenefitDetailView.as_view(), name="agent_benefit_detail"),
    path("<int:pk>/review/", html_views.AgentBenefitReviewView.as_view(), name="agent_benefit_review"),
]
