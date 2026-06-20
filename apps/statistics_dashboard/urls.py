from django.urls import path

from .views import NationalStatsDashboardView, StatsExportView

urlpatterns = [
    path(
        "portal/agent/statistics/",
        NationalStatsDashboardView.as_view(),
        name="national-stats",
    ),
    path(
        "portal/agent/statistics/export/",
        StatsExportView.as_view(),
        name="stats-export",
    ),
]
