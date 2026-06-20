from django.urls import path

from . import html_views

app_name = "citizen_claims"

urlpatterns = [
    path("", html_views.CitizenClaimListView.as_view(), name="citizen_claim_list"),
    path("new/", html_views.CitizenClaimCreateView.as_view(), name="citizen_claim_create"),
    path("<int:pk>/", html_views.CitizenClaimDetailView.as_view(), name="citizen_claim_detail"),
    path("<int:pk>/message/", html_views.CitizenClaimMessageView.as_view(), name="citizen_claim_message"),
    path("<int:pk>/rate/", html_views.CitizenClaimRateView.as_view(), name="citizen_claim_rate"),
]
