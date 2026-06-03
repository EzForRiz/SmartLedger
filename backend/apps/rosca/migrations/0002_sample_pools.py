from django.db import migrations


def create_sample_pools(apps, schema_editor):
    ROSCAGroup = apps.get_model("rosca", "ROSCAGroup")
    if ROSCAGroup.objects.exists():
        return
    ROSCAGroup.objects.bulk_create([
        ROSCAGroup(
            name="Gold Committee",
            monthly_contribution=5000,
            total_payout=50000,
            duration_months=10,
            is_active=True,
        ),
        ROSCAGroup(
            name="Silver Committee",
            monthly_contribution=3000,
            total_payout=30000,
            duration_months=10,
            is_active=True,
        ),
        ROSCAGroup(
            name="Platinum Committee",
            monthly_contribution=10000,
            total_payout=100000,
            duration_months=10,
            is_active=True,
        ),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ("rosca", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_sample_pools, migrations.RunPython.noop),
    ]
