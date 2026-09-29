from django.contrib import admin
from .models import CalculatorRecord, Complaint, ComplaintHistory, Enquiry, MemberProfile
from .models import PaymentOrder, Plan, Subscription


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "phone")


@admin.register(CalculatorRecord)
class CalculatorRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "calculator_type", "calories", "created_at")
    list_filter = ("calculator_type",)
    search_fields = ("user__username", "user__email")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("full_name", "category", "status", "created_at", "updated_at", "resolved_at", "closed_at")
    list_filter = ("status", "category", "preferred_contact")
    search_fields = ("full_name", "email", "phone", "description")
    readonly_fields = ("created_at", "updated_at", "resolved_at", "closed_at")


@admin.register(ComplaintHistory)
class ComplaintHistoryAdmin(admin.ModelAdmin):
    list_display = ("complaint", "previous_status", "new_status", "action", "created_at")
    list_filter = ("new_status",)
    search_fields = ("complaint__full_name", "complaint__email", "action")
    readonly_fields = ("created_at",)
    
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "is_active")
    search_fields = ("name",)

@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ("user", "gateway_order_id", "amount", "status", "created_at")
    search_fields = ("gateway_order_id", "gateway_payment_id", "user__username")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "start_date", "end_date", "status")
    search_fields = ("user__username", "plan__name")


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "enquiry_type", "status", "created_at", "updated_at")
    list_filter = ("status", "enquiry_type")
    search_fields = ("full_name", "email", "phone", "message")
    readonly_fields = ("created_at", "updated_at")