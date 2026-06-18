from rest_framework.routers import DefaultRouter
from .views import AffiliateViewSet, DependentViewSet

router = DefaultRouter()
router.register(r"affiliates", AffiliateViewSet, basename="affiliate")

urlpatterns = router.urls
