from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("star", "0002_calculatorrecord"),
    ]

    operations = [
        migrations.CreateModel(
            name="Complaint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=30)),
                ("category", models.CharField(choices=[("facilities", "Gym Facilities"), ("equipment", "Equipment"), ("trainer", "Trainer"), ("membership", "Membership"), ("cleanliness", "Cleanliness"), ("other", "Other")], max_length=20)),
                ("description", models.TextField()),
                ("preferred_contact", models.CharField(choices=[("email", "Email"), ("phone", "Phone")], max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Enquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=30)),
                ("enquiry_type", models.CharField(choices=[("membership", "Membership"), ("personal_training", "Personal Training"), ("fitness_programs", "Fitness Programs"), ("pricing", "Pricing"), ("trainers", "Trainers"), ("facilities", "Gym Facilities"), ("other", "Other")], max_length=25)),
                ("message", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
