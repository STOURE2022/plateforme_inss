from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VerifyCardView, VerificationLogViewSet, VerificationStatsView

urlpatterns = [
    path("verify/stats/", VerificationStatsView.as_view(), name="verify-stats"),
    path("verify/", VerifyCardView.as_view(), name="verify-card"),
]

router = DefaultRouter()
router.register(r"verification-logs", VerificationLogViewSet, basename="verification-log")

urlpatterns += router.urls
