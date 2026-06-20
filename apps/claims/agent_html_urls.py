from django.urls import path

from . import html_views

app_name = "agent_claims"

urlpatterns = [
    path("", html_views.AgentClaimListView.as_view(), name="agent_claim_list"),
    path("<int:pk>/", html_views.AgentClaimDetailView.as_view(), name="agent_claim_detail"),
    path("<int:pk>/action/", html_views.AgentClaimActionView.as_view(), name="agent_claim_action"),
    path("<int:pk>/message/", html_views.AgentClaimMessageView.as_view(), name="agent_claim_message"),
]
