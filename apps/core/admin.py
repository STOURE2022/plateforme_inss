from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Contacto", {
            "fields": ("contact_email", "contact_phone", "contact_address", "contact_hours"),
        }),
        ("Visibilidade & Estado", {
            "fields": ("show_api_docs", "system_status_label"),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirect list view directly to the single object
        obj, _ = SiteSettings.objects.get_or_create(pk=1)
        return HttpResponseRedirect(
            reverse("admin:core_sitesettings_change", args=[obj.pk])
        )
