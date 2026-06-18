from django.urls import path
from . import html_views

urlpatterns = [
    path("", html_views.EmployerDashboardView.as_view(), name="employer-dashboard"),
    path("profile/", html_views.EmployerProfileView.as_view(), name="employer-profile"),
    path("contributions/", html_views.EmployerContributionsView.as_view(), name="employer-contributions"),
    path("contributions/new/", html_views.EmployerContributionCreateView.as_view(), name="employer-contribution-create"),
    path("contributions/calculate/", html_views.EmployerContributionCalculateView.as_view(), name="employer-contribution-calculate"),
]
