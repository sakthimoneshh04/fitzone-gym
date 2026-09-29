from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_default_plans(apps, schema_editor):
    Plan = apps.get_model("star", "Plan")
    Plan.objects.bulk_create([
        Plan(name="Foundation", slug="foundation", price="999.00", duration_days=30, features=["Gym floor access", "Locker access", "Fitness orientation"]),
        Plan(name="Performance", slug="performance", price="2499.00", duration_days=90, features=["Gym floor access", "Locker access", "Monthly coach check-in", "Progress tracking"]),
        Plan(name="All Access", slug="all-access", price="7999.00", duration_days=365, features=["24/7 gym access", "Personalised training guidance", "Priority coach support", "Progress tracking"]),
    ])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("star", "0006_workoutplan_workoutcompletion_dietplan"),
    ]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("duration_days", models.PositiveIntegerField()),
                ("features", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("price", "name")},
        ),
        migrations.CreateModel(
            name="PaymentOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("gateway_order_id", models.CharField(max_length=100, unique=True)),
                ("gateway_payment_id", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("gateway_signature", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=12)),
                ("failure_reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_orders", to="star.plan")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_orders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("gateway_subscription_id", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("active", "Active"), ("expired", "Expired"), ("cancelled", "Cancelled")], default="pending", max_length=12)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("payment_order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="subscription", to="star.paymentorder")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscriptions", to="star.plan")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscriptions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.RunPython(create_default_plans, migrations.RunPython.noop),
    ]
