from django.core.management.base import BaseCommand

from apps.benefits.models import BenefitType, BenefitCategory, CalculationMethod


BENEFIT_TYPES_DATA = [
    {
        "category": BenefitCategory.RETIREMENT,
        "name": "Pensão de Reforma",
        "description": (
            "Pensão paga aos trabalhadores que atingiram a idade de reforma e "
            "cumpriram o período mínimo de contribuições."
        ),
        "min_contribution_months": 180,  # 15 anos
        "calculation_method": CalculationMethod.PERCENTAGE,
        "fixed_amount": None,
        "percentage_of_salary": 60,
    },
    {
        "category": BenefitCategory.DISABILITY,
        "name": "Pensão de Invalidez",
        "description": (
            "Pensão paga a trabalhadores que sofreram perda permanente e total "
            "da capacidade de trabalho por doença ou acidente não profissional."
        ),
        "min_contribution_months": 36,  # 3 anos
        "calculation_method": CalculationMethod.PERCENTAGE,
        "fixed_amount": None,
        "percentage_of_salary": 50,
    },
    {
        "category": BenefitCategory.SURVIVOR,
        "name": "Pensão de Sobrevivência",
        "description": (
            "Pensão paga aos dependentes do trabalhador falecido que estava "
            "inscrito no INSS ou já era beneficiário de uma pensão."
        ),
        "min_contribution_months": 0,
        "calculation_method": CalculationMethod.PERCENTAGE,
        "fixed_amount": None,
        "percentage_of_salary": 50,
    },
    {
        "category": BenefitCategory.FAMILY,
        "name": "Abono de Família",
        "description": (
            "Subsídio mensal pago ao trabalhador com filhos menores ou "
            "dependentes a cargo."
        ),
        "min_contribution_months": 6,
        "calculation_method": CalculationMethod.FIXED,
        "fixed_amount": 5000,
        "percentage_of_salary": None,
    },
    {
        "category": BenefitCategory.SICKNESS,
        "name": "Subsídio de Doença",
        "description": (
            "Subsídio temporário pago ao trabalhador que se encontra "
            "incapacitado para o trabalho por motivo de doença."
        ),
        "min_contribution_months": 3,
        "calculation_method": CalculationMethod.PERCENTAGE,
        "fixed_amount": None,
        "percentage_of_salary": 70,
    },
    {
        "category": BenefitCategory.WORK_ACCIDENT,
        "name": "Acidente de Trabalho",
        "description": (
            "Prestação paga ao trabalhador vítima de acidente de trabalho "
            "ou doença profissional, independentemente do tempo de contribuição."
        ),
        "min_contribution_months": 0,
        "calculation_method": CalculationMethod.PERCENTAGE,
        "fixed_amount": None,
        "percentage_of_salary": 80,
    },
    {
        "category": BenefitCategory.DEATH,
        "name": "Subsídio de Morte",
        "description": (
            "Subsídio único pago à família do trabalhador falecido "
            "para fazer face às despesas imediatas com o funeral."
        ),
        "min_contribution_months": 12,
        "calculation_method": CalculationMethod.FIXED,
        "fixed_amount": 50000,
        "percentage_of_salary": None,
    },
]


class Command(BaseCommand):
    help = "Seed standard benefit types for Guinea-Bissau INSS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing benefit types before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = BenefitType.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing benefit types."))

        created_count = 0
        updated_count = 0

        for data in BENEFIT_TYPES_DATA:
            obj, created = BenefitType.objects.update_or_create(
                category=data["category"],
                name=data["name"],
                defaults={
                    "description": data["description"],
                    "min_contribution_months": data["min_contribution_months"],
                    "calculation_method": data["calculation_method"],
                    "fixed_amount": data["fixed_amount"],
                    "percentage_of_salary": data["percentage_of_salary"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  [CRIADO] {obj.name}"))
            else:
                updated_count += 1
                self.stdout.write(f"  [ATUALIZADO] {obj.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nConcluído: {created_count} criados, {updated_count} atualizados."
            )
        )
