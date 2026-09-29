from django.conf import settings
from django.db import models
from django.utils import timezone


class MemberProfile(models.Model):
    ROLE_CHOICES = [
        ("coach", "Coach"),
        ("client", "Client"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member_profile",
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Plan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("price", "name")

    def __str__(self):
        return self.name


class PaymentOrder(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_orders")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="payment_orders")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    gateway_order_id = models.CharField(max_length=100, unique=True)
    gateway_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    gateway_signature = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} - {self.gateway_order_id}"


class Subscription(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    payment_order = models.OneToOneField(PaymentOrder, on_delete=models.PROTECT, related_name="subscription")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gateway_subscription_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def refresh_status(self, save=True):
        if self.status == "active" and self.end_date and self.end_date < timezone.localdate():
            self.status = "expired"
            if save:
                self.save(update_fields=("status", "updated_at"))
        return self.status

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} - {self.status}"


class CalculatorRecord(models.Model):
    CALCULATOR_CHOICES = (("calorie", "Calorie calculator"), ("macro", "Macro calculator"))

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calculator_records",
    )
    calculator_type = models.CharField(max_length=10, choices=CALCULATOR_CHOICES)
    age = models.PositiveIntegerField()
    sex = models.CharField(max_length=10)
    height_cm = models.DecimalField(max_digits=6, decimal_places=2)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)
    activity = models.DecimalField(max_digits=4, decimal_places=2)
    calories = models.PositiveIntegerField()
    protein_grams = models.PositiveIntegerField()
    carbohydrate_grams = models.PositiveIntegerField()
    fat_grams = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} - {self.get_calculator_type_display()}"


class Complaint(models.Model):
    CATEGORY_CHOICES = (
        ("facilities", "Gym Facilities"),
        ("equipment", "Equipment"),
        ("trainer", "Trainer"),
        ("membership", "Membership"),
        ("cleanliness", "Cleanliness"),
        ("other", "Other"),
    )
    CONTACT_CHOICES = (
        ("email", "Email"),
        ("phone", "Phone"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("under_review", "Under Review"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    )

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    preferred_contact = models.CharField(max_length=10, choices=CONTACT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        previous_status = None
        if not is_new:
            previous_status = type(self).objects.only("status").get(pk=self.pk).status

        if self.status == "resolved" and self.resolved_at is None:
            from django.utils import timezone
            self.resolved_at = timezone.now()
        if self.status == "closed" and self.closed_at is None:
            from django.utils import timezone
            self.closed_at = timezone.now()

        super().save(*args, **kwargs)

        if is_new:
            ComplaintHistory.objects.create(
                complaint=self,
                previous_status="",
                new_status=self.status,
                action="Complaint submitted",
            )
        elif previous_status != self.status:
            ComplaintHistory.objects.create(
                complaint=self,
                previous_status=previous_status,
                new_status=self.status,
                action=f"Status changed to {self.get_status_display()}",
            )


class ComplaintHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="history")
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=Complaint.STATUS_CHOICES)
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)


class Enquiry(models.Model):
    TYPE_CHOICES = (
        ("membership", "Membership"),
        ("personal_training", "Personal Training"),
        ("fitness_programs", "Fitness Programs"),
        ("pricing", "Pricing"),
        ("trainers", "Trainers"),
        ("facilities", "Gym Facilities"),
        ("other", "Other"),
    )

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    enquiry_type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=(
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("responded", "Responded"),
            ("closed", "Closed"),
        ),
        default="new",
    )
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)


class DietPlan(models.Model):
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="diet_plans")
    client = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="diet_plans")
    goal = models.CharField(max_length=150)
    breakfast = models.TextField()
    lunch = models.TextField()
    dinner = models.TextField()
    snacks = models.TextField(blank=True)
    water_intake = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)


class WorkoutPlan(models.Model):
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workout_plans")
    client = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="workout_plans")
    goal = models.CharField(max_length=150)
    workout_date = models.DateField()
    exercise = models.CharField(max_length=200)
    sets = models.PositiveIntegerField()
    reps = models.PositiveIntegerField()
    duration = models.CharField(max_length=100, blank=True)
    rest_time = models.CharField(max_length=100, blank=True)
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-workout_date", "exercise")


class WorkoutCompletion(models.Model):
    STATUS_CHOICES = (("pending", "Pending"), ("completed", "Completed"))

    workout = models.OneToOneField(WorkoutPlan, on_delete=models.CASCADE, related_name="completion")
    client = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="workout_completions")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    completed_on = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
