from django.db import models


class SiteSettings(models.Model):
    """Singleton model — only one row should exist."""

    # Contact info
    contact_email = models.EmailField(default="suporte@inss.gw", verbose_name="Email de suporte")
    contact_phone = models.CharField(max_length=30, default="+245 966 000 000", verbose_name="Telefone")
    contact_address = models.CharField(max_length=200, default="Av. dos Combatentes, Bissau", verbose_name="Endereço")
    contact_hours = models.CharField(max_length=100, default="Seg–Sex 08h–17h", verbose_name="Horário")

    # Footer / visibility
    show_api_docs = models.BooleanField(
        default=False,
        verbose_name="Mostrar links API docs no footer",
        help_text="Se activado, mostra Swagger, ReDoc e OpenAPI Schema no footer público.",
    )
    system_status_label = models.CharField(
        max_length=50, default="Sistema operacional", verbose_name="Estado do sistema"
    )

    class Meta:
        verbose_name = "Configurações do Site"
        verbose_name_plural = "Configurações do Site"

    def __str__(self):
        return "Configurações do Site"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
