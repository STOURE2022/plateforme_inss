"""
python manage.py seed_demo

Crée un jeu de données de démonstration complet pour e-INSS.
Idempotente : utilise get_or_create pour éviter les doublons.

Utilisateurs créés :
- admin@inss.gw / admin123! (ADMIN)
- agent@inss.gw / agent123! (AGENT)
- joao.silva@email.com / citizen123! (CITIZEN)
- maria.costa@email.com / citizen123! (CITIZEN)
- empresa.abc@email.com / employer123! (EMPLOYER)
- clinica.saude@email.com / provider123! (PROVIDER)
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Cria dados de demonstração para o e-INSS"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== seed_demo e-INSS ===\n"))

        # ------------------------------------------------------------------ #
        # 1. Utilizadores
        # ------------------------------------------------------------------ #
        from apps.accounts.models import UserRole

        users_data = [
            ("admin@inss.gw", "admin123!", UserRole.ADMIN, True, True),
            ("agent@inss.gw", "agent123!", UserRole.AGENT, True, True),
            ("joao.silva@email.com", "citizen123!", UserRole.CITIZEN, True, False),
            ("maria.costa@email.com", "citizen123!", UserRole.CITIZEN, True, False),
            ("empresa.abc@email.com", "employer123!", UserRole.EMPLOYER, True, False),
            ("clinica.saude@email.com", "provider123!", UserRole.PROVIDER, True, False),
        ]

        created_users = {}
        for email, password, role, is_active, is_staff in users_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"role": role, "is_active": is_active, "is_staff": is_staff},
            )
            if created:
                user.set_password(password)
                user.role = role
                user.save()
                self.stdout.write(f"  [+] Utilizador: {email}")
            else:
                self.stdout.write(f"  [=] Utilizador já existe: {email}")
            created_users[email] = user

        admin_user = created_users["admin@inss.gw"]
        agent_user = created_users["agent@inss.gw"]
        joao_user = created_users["joao.silva@email.com"]
        maria_user = created_users["maria.costa@email.com"]
        employer_user = created_users["empresa.abc@email.com"]

        # ------------------------------------------------------------------ #
        # 2. Afiliados
        # ------------------------------------------------------------------ #
        from apps.affiliates.models import Affiliate, Dependent, GenderChoices, RelationshipChoices, AffiliateStatus

        joao_affiliate, created = Affiliate.objects.get_or_create(
            user=joao_user,
            defaults={
                "niss": "GW0000000000001",
                "full_name": "João Silva",
                "birth_date": date(1985, 3, 15),
                "gender": GenderChoices.MALE,
                "nationality": "GW",
                "address": "Rua de Bissau, 123, Bissau",
                "phone": "+245 955 123 456",
                "status": AffiliateStatus.ACTIVE,
            },
        )
        if created:
            self.stdout.write("  [+] Afiliado: João Silva")
        else:
            self.stdout.write("  [=] Afiliado João Silva já existe")

        maria_affiliate, created = Affiliate.objects.get_or_create(
            user=maria_user,
            defaults={
                "niss": "GW0000000000002",
                "full_name": "Maria Costa",
                "birth_date": date(1990, 7, 22),
                "gender": GenderChoices.FEMALE,
                "nationality": "GW",
                "address": "Av. Amilcar Cabral, 45, Bissau",
                "phone": "+245 966 789 012",
                "status": AffiliateStatus.ACTIVE,
            },
        )
        if created:
            self.stdout.write("  [+] Afiliado: Maria Costa")
        else:
            self.stdout.write("  [=] Afiliado Maria Costa já existe")

        # ------------------------------------------------------------------ #
        # 3. Dependente (cônjuge de João)
        # ------------------------------------------------------------------ #
        dependent, created = Dependent.objects.get_or_create(
            affiliate=joao_affiliate,
            full_name="Ana Silva",
            defaults={
                "birth_date": date(1987, 11, 5),
                "relationship": RelationshipChoices.SPOUSE,
                "is_active": True,
            },
        )
        if created:
            self.stdout.write("  [+] Dependente: Ana Silva (cônjuge de João)")
        else:
            self.stdout.write("  [=] Dependente Ana Silva já existe")

        # ------------------------------------------------------------------ #
        # 4. Employer
        # ------------------------------------------------------------------ #
        from apps.employers.models import Employer, SectorChoices

        employer_profile, created = Employer.objects.get_or_create(
            user=employer_user,
            defaults={
                "company_name": "Empresa ABC Lda",
                "nuit": "NUIT0000000001",
                "sector": SectorChoices.PRIVATE,
                "address": "Zona Industrial, Bissau",
                "phone": "+245 320 456 789",
                "email": "empresa.abc@email.com",
                "registered_by": agent_user,
            },
        )
        if created:
            self.stdout.write("  [+] Employer: Empresa ABC Lda")
        else:
            self.stdout.write("  [=] Employer Empresa ABC Lda já existe")

        # ------------------------------------------------------------------ #
        # 5. Contribuições (João — 12 meses do ano anterior, PAID)
        # ------------------------------------------------------------------ #
        from apps.contributions.models import Contribution, ContributionStatus

        current_year = timezone.now().year
        prev_year = current_year - 1
        joao_contribs_created = 0

        for month in range(1, 13):
            _, created = Contribution.objects.get_or_create(
                affiliate=joao_affiliate,
                period_year=prev_year,
                period_month=month,
                defaults={
                    "employer": employer_profile,
                    "salary_base": Decimal("500000.00"),
                    "employee_rate": Decimal("0.0400"),
                    "employer_rate": Decimal("0.0800"),
                    "status": ContributionStatus.PAID,
                    "payment_date": date(prev_year, month, 10),
                    "created_by": agent_user,
                    "notes": "Contribuição demo",
                },
            )
            if created:
                joao_contribs_created += 1

        self.stdout.write(
            f"  [+] Contribuições João: {joao_contribs_created} criadas "
            f"({12 - joao_contribs_created} já existiam)"
        )

        # Maria — 3 meses PAID
        maria_contribs_created = 0
        for month in range(1, 4):
            _, created = Contribution.objects.get_or_create(
                affiliate=maria_affiliate,
                period_year=prev_year,
                period_month=month,
                defaults={
                    "employer": employer_profile,
                    "salary_base": Decimal("400000.00"),
                    "employee_rate": Decimal("0.0400"),
                    "employer_rate": Decimal("0.0800"),
                    "status": ContributionStatus.PAID,
                    "payment_date": date(prev_year, month, 15),
                    "created_by": agent_user,
                    "notes": "Contribuição demo",
                },
            )
            if created:
                maria_contribs_created += 1

        self.stdout.write(f"  [+] Contribuições Maria: {maria_contribs_created} criadas")

        # ------------------------------------------------------------------ #
        # 6. HealthCards (um para cada afiliado)
        # ------------------------------------------------------------------ #
        from apps.cards.models import HealthCard, CardStatus

        joao_card, created = HealthCard.objects.get_or_create(
            affiliate=joao_affiliate,
            defaults={
                "status": CardStatus.ACTIVE,
                "created_by": agent_user,
            },
        )
        if created:
            self.stdout.write(f"  [+] Cartão João: {joao_card.card_number}")
        else:
            self.stdout.write(f"  [=] Cartão João já existe: {joao_card.card_number}")

        maria_card, created = HealthCard.objects.get_or_create(
            affiliate=maria_affiliate,
            defaults={
                "status": CardStatus.ACTIVE,
                "created_by": agent_user,
            },
        )
        if created:
            self.stdout.write(f"  [+] Cartão Maria: {maria_card.card_number}")
        else:
            self.stdout.write(f"  [=] Cartão Maria já existe: {maria_card.card_number}")

        # ------------------------------------------------------------------ #
        # 7. VerificationLogs (10 simulados)
        # ------------------------------------------------------------------ #
        from apps.verification.models import VerificationLog, VerificationResult

        provider_user = created_users["clinica.saude@email.com"]
        verif_created = 0
        existing_count = VerificationLog.objects.filter(card=joao_card).count()

        if existing_count < 10:
            for i in range(10 - existing_count):
                result = VerificationResult.SUCCESS if i % 3 != 0 else VerificationResult.FAILURE
                VerificationLog.objects.create(
                    verifier=provider_user,
                    verifier_ip="192.168.1.100",
                    verifier_role="PROVIDER",
                    card=joao_card,
                    card_number=joao_card.card_number,
                    token_jti=f"demo-jti-{i:04d}",
                    result=result,
                    failure_reason="" if result == VerificationResult.SUCCESS else "Token expirado",
                    response_ms=50 + i * 10,
                )
                verif_created += 1

        self.stdout.write(f"  [+] VerificationLogs: {verif_created} criados")

        # ------------------------------------------------------------------ #
        # 8. Notifications (5 não lidas para João)
        # ------------------------------------------------------------------ #
        from apps.notifications.models import Notification, NotificationType

        notif_messages = [
            ("Bem-vindo ao e-INSS", "A sua conta foi criada com sucesso.", NotificationType.SUCCESS),
            ("Cotização paga", "A sua cotização de Janeiro foi registada.", NotificationType.INFO),
            ("Cartão emitido", f"O seu cartão {joao_card.card_number} está pronto.", NotificationType.SUCCESS),
            ("Documento pendente", "Atualize o seu endereço no perfil.", NotificationType.WARNING),
            ("Atualização de sistema", "O portal estará em manutenção dia 20/06 às 23h.", NotificationType.INFO),
        ]

        notif_created = 0
        existing_notifs = Notification.objects.filter(recipient=joao_user).count()

        if existing_notifs < 5:
            for title, message, ntype in notif_messages[existing_notifs:]:
                Notification.objects.create(
                    recipient=joao_user,
                    title=title,
                    message=message,
                    notification_type=ntype,
                    is_read=False,
                )
                notif_created += 1

        self.stdout.write(f"  [+] Notificações: {notif_created} criadas para João")

        # ------------------------------------------------------------------ #
        # 9. AuditEvents (10 variados)
        # ------------------------------------------------------------------ #
        from apps.audit.models import AuditEvent
        from apps.audit.utils import log_event

        existing_audit = AuditEvent.objects.filter(
            action__startswith="demo."
        ).count()

        audit_created = 0
        if existing_audit < 10:
            audit_actions = [
                ("demo.login.success", joao_user, joao_card, {}),
                ("demo.login.success", maria_user, maria_card, {}),
                ("demo.affiliate.created", agent_user, joao_affiliate, {"via": "portal"}),
                ("demo.affiliate.created", agent_user, maria_affiliate, {"via": "portal"}),
                ("demo.card.created", agent_user, joao_card, {}),
                ("demo.card.created", agent_user, maria_card, {}),
                ("demo.contribution.paid", agent_user, None, {"period": f"{prev_year}/01"}),
                ("demo.card.verified", provider_user, joao_card, {"result": "SUCCESS"}),
                ("demo.card.verified", provider_user, joao_card, {"result": "FAILURE"}),
                ("demo.admin.login", admin_user, None, {"ip": "10.0.0.1"}),
            ]
            for i, (action, actor, resource, details) in enumerate(audit_actions[existing_audit:]):
                log_event(action=action, user=actor, resource=resource, details=details)
                audit_created += 1

        self.stdout.write(f"  [+] AuditEvents: {audit_created} criados")

        # ------------------------------------------------------------------ #
        # Resumo
        # ------------------------------------------------------------------ #
        self.stdout.write("\n" + self.style.SUCCESS("=== Resumo seed_demo ==="))
        self.stdout.write(f"  Utilizadores : {User.objects.count()}")
        self.stdout.write(f"  Afiliados    : {Affiliate.objects.count()}")
        self.stdout.write(f"  Employers    : {Employer.objects.count()}")
        self.stdout.write(f"  Contribuições: {Contribution.objects.count()}")
        self.stdout.write(f"  Cartões      : {HealthCard.objects.count()}")
        self.stdout.write(f"  Verificações : {VerificationLog.objects.count()}")
        self.stdout.write(f"  Notificações : {Notification.objects.count()}")
        self.stdout.write(f"  Audit events : {AuditEvent.objects.count()}")
        self.stdout.write(self.style.SUCCESS("\nDados de demonstração prontos!"))
        self.stdout.write("\nCredenciais:")
        self.stdout.write("  admin@inss.gw          / admin123!")
        self.stdout.write("  agent@inss.gw          / agent123!")
        self.stdout.write("  joao.silva@email.com   / citizen123!")
        self.stdout.write("  maria.costa@email.com  / citizen123!")
        self.stdout.write("  empresa.abc@email.com  / employer123!")
        self.stdout.write("  clinica.saude@email.com/ provider123!")
