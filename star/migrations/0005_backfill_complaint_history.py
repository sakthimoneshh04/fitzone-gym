from django.db import migrations


def backfill_history(apps, schema_editor):
    Complaint = apps.get_model("star", "Complaint")
    ComplaintHistory = apps.get_model("star", "ComplaintHistory")
    ComplaintHistory.objects.bulk_create(
        ComplaintHistory(
            complaint=complaint,
            previous_status="",
            new_status=complaint.status,
            action="Complaint submitted",
        )
        for complaint in Complaint.objects.all()
        if not ComplaintHistory.objects.filter(complaint=complaint).exists()
    )


class Migration(migrations.Migration):

    dependencies = [
        ("star", "0004_complaint_tracking_enquiry_tracking"),
    ]

    operations = [
        migrations.RunPython(backfill_history, migrations.RunPython.noop),
    ]
