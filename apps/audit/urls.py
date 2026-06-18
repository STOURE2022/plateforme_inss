from rest_framework.routers import DefaultRouter
from apps.audit.views import AuditEventViewSet

router = DefaultRouter()
router.register(r"audit", AuditEventViewSet, basename="audit")

urlpatterns = router.urls
