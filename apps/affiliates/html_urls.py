from django.urls import path
from . import html_views

urlpatterns = [
    path("", html_views.CitizenDashboardView.as_view(), name="citizen-dashboard"),
    path("card/", html_views.CitizenCardView.as_view(), name="citizen-card"),
    path("card/qr/", html_views.CitizenCardQRView.as_view(), name="citizen-card-qr"),
    path("contributions/", html_views.CitizenContributionsView.as_view(), name="citizen-contributions"),
    path("dependents/", html_views.CitizenDependentsView.as_view(), name="citizen-dependents"),
]
