from django.urls import path

from . import html_views

# Citizen claim URLs — mounted at /portal/citizen/claims/
citizen_urlpatterns = [
    path("", html_views.CitizenClaimListView.as_view(), name="citizen_claim_list"),
    path("new/", html_views.CitizenClaimCreateView.as_view(), name="citizen_claim_create"),
    path("<int:pk>/", html_views.CitizenClaimDetailView.as_view(), name="citizen_claim_detail"),
    path("<int:pk>/message/", html_views.CitizenClaimMessageView.as_view(), name="citizen_claim_message"),
    path("<int:pk>/rate/", html_views.CitizenClaimRateView.as_view(), name="citizen_claim_rate"),
]

# Agent claim URLs — mounted at /portal/agent/claims/
agent_urlpatterns = [
    path("", html_views.AgentClaimListView.as_view(), name="agent_claim_list"),
    path("<int:pk>/", html_views.AgentClaimDetailView.as_view(), name="agent_claim_detail"),
    path("<int:pk>/action/", html_views.AgentClaimActionView.as_view(), name="agent_claim_action"),
    path("<int:pk>/message/", html_views.AgentClaimMessageView.as_view(), name="agent_claim_message"),
]
