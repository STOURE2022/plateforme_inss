from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.shortcuts import render

from apps.notifications.models import Notification


class NotificationDropdownView(LoginRequiredMixin, View):
    """
    GET /notifications/dropdown/
    Fragment HTML pour la cloche de notifications dans la sidebar.
    Retourne les 5 dernières notifications non lues.
    Appelé via hx-get dans base_portal.html.
    """

    def get(self, request, *args, **kwargs):
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).order_by("-created_at")[:5]

        return render(
            request,
            "notifications/dropdown.html",
            {"notifications": notifications},
        )
