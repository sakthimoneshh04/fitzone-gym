from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("star", "0003_complaint_enquiry"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="closed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="complaint",
            name="response",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="complaint",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="complaint",
            name="status",
            field=models.CharField(choices=[("pending", "Pending"), ("under_review", "Under Review"), ("resolved", "Resolved"), ("closed", "Closed")], default="pending", max_length=20),
        ),
        migrations.AddField(
            model_name="complaint",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="enquiry",
            name="response",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="enquiry",
            name="status",
            field=models.CharField(choices=[("new", "New"), ("in_progress", "In Progress"), ("responded", "Responded"), ("closed", "Closed")], default="new", max_length=20),
        ),
        migrations.AddField(
            model_name="enquiry",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.CreateModel(
            name="ComplaintHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(blank=True, max_length=20)),
                ("new_status", models.CharField(choices=[("pending", "Pending"), ("under_review", "Under Review"), ("resolved", "Resolved"), ("closed", "Closed")], max_length=20)),
                ("action", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="history", to="star.complaint")),
            ],
            options={"ordering": ("created_at",)},
        ),
    ]
