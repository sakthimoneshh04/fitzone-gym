import hashlib
import hmac
import importlib
import json
from datetime import timedelta
from decimal import Decimal

try:
    razorpay = importlib.import_module("razorpay")
except ImportError:
    razorpay = None

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .email_service import (
    send_complaint_notification,
    send_enquiry_notification,
    send_login_notification,
    send_payment_success_email,
    send_plan_assignment_email,
    send_welcome_email,
)
from .forms import (CalculatorForm, ComplaintForm, ComplaintUpdateForm, DietPlanForm, EnquiryForm,
                    EnquiryUpdateForm, RegistrationForm, WorkoutCompletionForm, WorkoutPlanForm)
from .models import (CalculatorRecord, Complaint, DietPlan, Enquiry, MemberProfile, PaymentOrder, Plan,
                      Subscription, WorkoutCompletion, WorkoutPlan)


def index(request):
    return render(request,"index.html")


def _payment_client():
    if razorpay is None or not settings.PAYMENT_KEY_ID or not settings.PAYMENT_KEY_SECRET:
        raise RuntimeError(getattr(settings, "PAYMENT_CONFIG_ERROR", "Payment gateway is not configured."))
    return razorpay.Client(auth=(settings.PAYMENT_KEY_ID, settings.PAYMENT_KEY_SECRET))


def _expected_amount_in_paise(amount):
    return int(Decimal(str(amount)) * Decimal("100"))


def _subscription_payload(subscription):
    subscription.refresh_status()
    return {
        "plan": subscription.plan.name,
        "status": subscription.get_status_display(),
        "start_date": subscription.start_date.isoformat() if subscription.start_date else "",
        "end_date": subscription.end_date.isoformat() if subscription.end_date else "",
    }


def _activate_payment(payment, payment_id, signature="", payment_method=""):
    with transaction.atomic():
        payment = PaymentOrder.objects.select_for_update().select_related("plan", "user").get(pk=payment.pk)
        if payment.status == "paid":
            return payment.subscription
        payment.status = "paid"
        payment.gateway_payment_id = payment_id
        payment.gateway_signature = signature
        payment.payment_method = payment_method
        payment.failure_reason = ""
        payment.save(update_fields=("status", "gateway_payment_id", "gateway_signature", "payment_method", "failure_reason", "updated_at"))
        Subscription.objects.filter(user=payment.user, status="active").update(
            status="cancelled", updated_at=timezone.now()
        )
        subscription, created = Subscription.objects.get_or_create(
            payment_order=payment,
            defaults={
                "user": payment.user,
                "plan": payment.plan,
                "amount": payment.amount,
                "status": "active",
                "start_date": timezone.localdate(),
                "end_date": timezone.localdate() + timedelta(days=payment.plan.duration_days),
            },
        )
        if not created and subscription.status != "active":
            subscription.status = "active"
            subscription.start_date = subscription.start_date or timezone.localdate()
            subscription.end_date = subscription.end_date or (
                subscription.start_date + timedelta(days=payment.plan.duration_days)
            )
            subscription.save(update_fields=("status", "start_date", "end_date", "updated_at"))
        return subscription


def _fail_payment(payment, reason="Payment was not completed", status="failed"):
    if payment.status == "pending":
        payment.status = status
        payment.failure_reason = reason[:255]
        payment.save(update_fields=("status", "failure_reason", "updated_at"))


def about(request):
    return render(request,"about.html")


def services(request):
    return render(request,"services.html")


def complaint(request):
    form = ComplaintForm(request.POST or None)
    submitted = False
    if request.method == "POST" and form.is_valid():
        complaint = form.save()
        send_complaint_notification(complaint)
        submitted = True
        form = ComplaintForm()
    return render(request, "complaint.html", {"form": form, "submitted": submitted})


def enquiry(request):
    form = EnquiryForm(request.POST or None)
    submitted = False
    if request.method == "POST" and form.is_valid():
        enquiry = form.save()
        send_enquiry_notification(enquiry)
        submitted = True
        form = EnquiryForm()
    return render(request, "enquiry.html", {"form": form, "submitted": submitted})


def contact(request):
    return render(request,"contact.html")


def subscription_plans(request):
    plans = Plan.objects.filter(is_active=True)
    current_subscription = None
    payment_history = []
    if request.user.is_authenticated:
        current_subscription = (Subscription.objects.filter(user=request.user)
                                .select_related("plan", "payment_order").first())
        if current_subscription:
            current_subscription.refresh_status()
        payment_history = PaymentOrder.objects.filter(user=request.user).select_related("plan")[:10]
    return render(request, "subscription_plans.html", {
        "plans": plans,
        "current_subscription": current_subscription,
        "payment_history": payment_history,
        "payment_key_id": settings.PAYMENT_KEY_ID,
    })


@login_required
@require_POST
def create_payment_order(request):
    if request.user.member_profile.role != "client":
        return JsonResponse({"error": "Only client accounts can purchase a subscription."}, status=403)
    try:
        plan_id = request.POST.get("plan_id")
        plan = Plan.objects.get(pk=plan_id, is_active=True)
        client = _payment_client()
        amount = _expected_amount_in_paise(plan.price)
        currency = "INR"
        order = client.order.create({
            "amount": amount,
            "currency": currency,
            "receipt": f"fitzone-{request.user.pk}-{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
            "notes": {"user_id": str(request.user.pk), "plan_id": str(plan.pk)},
        })
        order_id = order.get("id")
        if not order_id:
            raise ValueError("Razorpay order ID was not returned")
        payment = PaymentOrder.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            currency=currency,
            status="pending",
            gateway_order_id=order_id,
        )
        return JsonResponse({
            "key": settings.PAYMENT_KEY_ID,
            "order_id": payment.gateway_order_id,
            "amount": amount,
            "currency": currency,
            "plan": plan.name,
            "user_name": request.user.get_full_name() or request.user.username,
            "user_email": request.user.email,
        })
    except Plan.DoesNotExist:
        return JsonResponse({"error": "The selected plan is no longer available."}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except (KeyError, ValueError, TypeError):
        return JsonResponse({"error": "Payments are temporarily unavailable. Please try again later."}, status=503)
    except Exception:
        return JsonResponse({"error": "Unable to start payment. Please try again later."}, status=502)


@login_required
@require_POST
def verify_payment(request):
    try:
        data = json.loads(request.body)
        order_id = data["razorpay_order_id"]
        payment_id = data["razorpay_payment_id"]
        signature = data["razorpay_signature"]
        payment = PaymentOrder.objects.filter(gateway_order_id=order_id, user=request.user).select_related("plan", "user").first()
        if payment is None:
            return JsonResponse({"error": "The payment order could not be found."}, status=400)
        if payment.status == "paid":
            return JsonResponse({"success": True, "subscription": _subscription_payload(payment.subscription)})
        client = _payment_client()
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
        except Exception:
            _fail_payment(payment, "Razorpay signature verification failed.", status="failed")
            return JsonResponse({"error": "Payment verification failed."}, status=400)

        gateway_payment = client.payment.fetch(payment_id)
        expected_amount = _expected_amount_in_paise(payment.amount)
        if (gateway_payment.get("order_id") != order_id or
                gateway_payment.get("amount") != expected_amount or
                gateway_payment.get("currency") != (payment.currency or "INR") or
                gateway_payment.get("status") not in {"captured", "paid"}):
            _fail_payment(payment, "Payment did not match the local order or was not captured.", status="failed")
            return JsonResponse({"error": "Payment was not captured or did not match the order."}, status=400)
        subscription = _activate_payment(payment, payment_id, signature, gateway_payment.get("method", ""))
        send_payment_success_email(payment)
        return JsonResponse({"success": True, "subscription": _subscription_payload(subscription)})
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "The payment response was invalid."}, status=400)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except Exception:
        if "payment" in locals():
            _fail_payment(payment, "Payment verification failed. No subscription was activated.", status="failed")
        return JsonResponse({"error": "Payment verification failed. No subscription was activated."}, status=400)


@login_required
@require_POST
def payment_failed(request):
    payment = PaymentOrder.objects.filter(
        gateway_order_id=request.POST.get("razorpay_order_id"), user=request.user, status="pending"
    ).first()
    if payment:
        status = "cancelled" if request.POST.get("status") == "cancelled" else "failed"
        _fail_payment(payment, request.POST.get("error_description") or "Payment was not completed", status)
    return JsonResponse({"success": True})


@csrf_exempt
@require_POST
def payment_webhook(request):
    if not settings.PAYMENT_WEBHOOK_SECRET:
        return JsonResponse({"error": "Webhook is not configured."}, status=503)
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return JsonResponse({"error": "Invalid webhook signature."}, status=400)
    try:
        payload = json.loads(request.body)
        event = payload.get("event")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = entity.get("order_id")
        if not order_id:
            return JsonResponse({"error": "Invalid webhook payload."}, status=400)
        payment = PaymentOrder.objects.select_related("plan", "user").get(gateway_order_id=order_id)
        if payment.status == "paid":
            return JsonResponse({"received": True})
        expected_amount = _expected_amount_in_paise(payment.amount)
        if entity.get("amount") is not None and entity.get("amount") != expected_amount:
            return JsonResponse({"error": "Webhook amount mismatch."}, status=400)
        if entity.get("currency") and entity.get("currency") != payment.currency:
            return JsonResponse({"error": "Webhook currency mismatch."}, status=400)
        if event == "payment.captured" and entity.get("status") in {"captured", "paid"}:
            _activate_payment(payment, entity.get("id", ""), payment_method=entity.get("method", ""))
        elif event == "payment.failed":
            _fail_payment(payment, entity.get("error_description") or "Payment failed")
        return JsonResponse({"received": True})
    except (ValueError, KeyError, PaymentOrder.DoesNotExist):
        return JsonResponse({"error": "Invalid webhook payload."}, status=400)


def choose_role(request):
    if request.method == "POST":
        role = request.POST.get("role")

        if role == "coach":
            request.session["role"] = "coach"
            return redirect("register")

        if role == "client":
            request.session["role"] = "client"
            return redirect("register")

        return render(
            request,
            "choose_role.html",
            {"error": "Please select a valid role."},
        )

    return render(request,"choose_role.html")


@transaction.atomic
def register(request):
    form = RegistrationForm(request.POST or None, initial={"role": request.session.get("role")})
    if request.method == "POST" and form.is_valid():
        user = form.save()
        send_welcome_email(user)
        login(request, user)
        request.session.pop("role", None)
        return redirect("dashboard")
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        send_login_notification(request.user)
        return redirect("dashboard")
    return render(request, "login.html", {"form": form})


@login_required
def dashboard(request):
    profile = request.user.member_profile
    return redirect("coach_dashboard" if profile.role == "coach" else "client_dashboard")


@login_required
def coach_dashboard(request):
    if request.user.member_profile.role != "coach":
        return redirect("client_dashboard")
    clients = MemberProfile.objects.filter(role="client").select_related("user")
    diet_plans = list(DietPlan.objects.filter(coach=request.user).select_related("client__user"))
    workout_plans = list(WorkoutPlan.objects.filter(coach=request.user).select_related("client__user"))
    complaints = list(Complaint.objects.all())
    enquiries = list(Enquiry.objects.all())
    subscriptions = list(Subscription.objects.select_related("user", "plan", "payment_order").order_by("-created_at"))
    for subscription in subscriptions:
        subscription.refresh_status()
    payments = PaymentOrder.objects.select_related("user", "plan").order_by("-created_at")
    return render(request, "coach_dashboard.html", {
        "profile": request.user.member_profile,
        "recent_calculations": request.user.calculator_records.all()[:5],
        "client_count": clients.count(),
        "clients": clients,
        "complaint_items": [(item, ComplaintUpdateForm(instance=item)) for item in complaints],
        "enquiry_items": [(item, EnquiryUpdateForm(instance=item)) for item in enquiries],
        "diet_items": [(item, DietPlanForm(instance=item)) for item in diet_plans],
        "workout_items": [(item, WorkoutPlanForm(instance=item)) for item in workout_plans],
        "progress": WorkoutCompletion.objects.filter(workout__coach=request.user).select_related("workout", "client__user"),
        "diet_form": DietPlanForm(),
        "workout_form": WorkoutPlanForm(),
        "subscriptions": subscriptions,
        "payments": payments,
    })


def _coach_only(request):
    return request.user.is_authenticated and request.user.member_profile.role == "coach"


@login_required
def coach_diet_create(request):
    if not _coach_only(request):
        return redirect("client_dashboard")
    form = DietPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.coach = request.user
        plan.save()
        send_plan_assignment_email(plan, plan_type="diet", client_member=plan.client)
        return redirect("coach_dashboard")
    return redirect("coach_dashboard")


@login_required
def coach_diet_edit(request, pk):
    if not _coach_only(request):
        return redirect("client_dashboard")
    plan = get_object_or_404(DietPlan, pk=pk, coach=request.user)
    form = DietPlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
    return redirect("coach_dashboard")


@login_required
def coach_diet_delete(request, pk):
    if not _coach_only(request):
        return redirect("client_dashboard")
    plan = get_object_or_404(DietPlan, pk=pk, coach=request.user)
    if request.method == "POST":
        plan.delete()
    return redirect("coach_dashboard")


@login_required
def coach_workout_create(request):
    if not _coach_only(request):
        return redirect("client_dashboard")
    form = WorkoutPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.coach = request.user
        plan.save()
        WorkoutCompletion.objects.create(workout=plan, client=plan.client)
        send_plan_assignment_email(plan, plan_type="workout", client_member=plan.client)
    return redirect("coach_dashboard")


@login_required
def coach_workout_edit(request, pk):
    if not _coach_only(request):
        return redirect("client_dashboard")
    plan = get_object_or_404(WorkoutPlan, pk=pk, coach=request.user)
    form = WorkoutPlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        plan.completion.client = plan.client
        plan.completion.save(update_fields=("client", "updated_at"))
    return redirect("coach_dashboard")


@login_required
def coach_workout_delete(request, pk):
    if not _coach_only(request):
        return redirect("client_dashboard")
    plan = get_object_or_404(WorkoutPlan, pk=pk, coach=request.user)
    if request.method == "POST":
        plan.delete()
    return redirect("coach_dashboard")


@login_required
def coach_complaint_update(request, pk):
    if not _coach_only(request):
        return redirect("client_dashboard")
    complaint = get_object_or_404(Complaint, pk=pk)
    form = ComplaintUpdateForm(request.POST or None, instance=complaint)
    if request.method == "POST" and form.is_valid():
        form.save()
    return redirect("coach_dashboard")


@login_required
def coach_enquiry_update(request, pk):
    if not _coach_only(request):
        return redirect("client_dashboard")
    enquiry = get_object_or_404(Enquiry, pk=pk)
    form = EnquiryUpdateForm(request.POST or None, instance=enquiry)
    if request.method == "POST" and form.is_valid():
        form.save()
    return redirect("coach_dashboard")


@login_required
def client_dashboard(request):
    if request.user.member_profile.role != "client":
        return redirect("coach_dashboard")
    profile = request.user.member_profile
    completions = WorkoutCompletion.objects.filter(client=profile).select_related("workout")
    if request.method == "POST":
        completion = get_object_or_404(completions, pk=request.POST.get("completion_id"))
        form = WorkoutCompletionForm(request.POST, instance=completion)
        if form.is_valid():
            form.save()
            return redirect("client_dashboard")
    return render(request, "client_dashboard.html", {
        "profile": profile,
        "recent_calculations": request.user.calculator_records.all()[:5],
        "diet_plans": DietPlan.objects.filter(client=profile).select_related("coach"),
        "workout_completions": completions,
        "workout_items": [(item, WorkoutCompletionForm(instance=item)) for item in completions],
    })


@login_required
def calculator(request, calculator_type):
    if calculator_type not in ("macro", "calorie"):
        return redirect("dashboard")
    form = CalculatorForm(request.POST or None)
    result = None
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        bmr = (10 * float(data["weight_kg"])) + (6.25 * float(data["height_cm"])) - (5 * data["age"])
        bmr += 5 if data["sex"] == "male" else -161
        calories = round(bmr * float(data["activity"]))
        protein = round(float(data["weight_kg"]) * 1.8)
        fat = round((calories * 0.25) / 9)
        carbohydrate = max(round((calories - (protein * 4) - (fat * 9)) / 4), 0)
        CalculatorRecord.objects.create(user=request.user, calculator_type=calculator_type, calories=calories, protein_grams=protein, carbohydrate_grams=carbohydrate, fat_grams=fat, **data)
        result = {"calories": calories, "protein": protein, "carbohydrate": carbohydrate, "fat": fat}
    return render(request, f"{calculator_type}_calculator.html", {"form": form, "result": result})


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("index")