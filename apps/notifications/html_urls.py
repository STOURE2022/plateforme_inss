from django.urls import path
from apps.notifications.html_views import NotificationDropdownView

urlpatterns = [
    path("dropdown/", NotificationDropdownView.as_view(), name="notifications-dropdown"),
]
