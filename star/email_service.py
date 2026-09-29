import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def _send_email(subject, message, recipient_list, *, cc=None):
    recipients = list(recipient_list or [])
    if not recipients:
        return False
    if cc:
        recipients = recipients + [email for email in cc if email]
    try:
        return bool(send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True))
    except Exception:
        logger.exception("Failed to send email: %s", subject)
        return False


def send_welcome_email(user):
    if not user or not getattr(user, "email", None):
        return False
    context = {
        "user_name": user.get_full_name() or user.username,
        "username": user.username,
    }
    subject = "Welcome to FitZone Gym"
    message = render_to_string("emails/welcome_email.txt", context)
    return _send_email(subject, message, [user.email])


def send_login_notification(user):
    recipient = getattr(settings, "ADMIN_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
    if not user or not recipient:
        return False
    user_email = getattr(user, "email", None) or "Not provided"
    message = (
        "A user successfully logged into FitZone Gym.\n\n"
        f"Username: {user.get_username()}\n"
        f"User email: {user_email}\n"
        f"Login date and time: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )
    try:
        send_mail(
            "New User Login - FitZone Gym",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send login notification for user: %s", user.get_username())
        return False


def send_enquiry_notification(enquiry):
    if not enquiry:
        return False
    admin_email = getattr(settings, "ADMIN_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL", None)
    if not admin_email:
        return False
    context = {
        "full_name": enquiry.full_name,
        "email": enquiry.email,
        "phone": enquiry.phone,
        "enquiry_type": enquiry.get_enquiry_type_display(),
        "message": enquiry.message,
    }
    subject = f"New enquiry from {enquiry.full_name}"
    message = render_to_string("emails/enquiry_notification.txt", context)
    sent = _send_email(subject, message, [admin_email])
    if enquiry.email:
        confirm_subject = "We received your FitZone enquiry"
        confirm_message = render_to_string("emails/enquiry_confirmation.txt", {
            "full_name": enquiry.full_name,
            "enquiry_type": enquiry.get_enquiry_type_display(),
        })
        _send_email(confirm_subject, confirm_message, [enquiry.email])
    return sent


def send_complaint_notification(complaint):
    if not complaint:
        return False
    admin_email = getattr(settings, "ADMIN_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL", None)
    if not admin_email:
        return False
    context = {
        "full_name": complaint.full_name,
        "email": complaint.email,
        "phone": complaint.phone,
        "category": complaint.get_category_display(),
        "description": complaint.description,
        "preferred_contact": complaint.get_preferred_contact_display(),
    }
    subject = f"New complaint from {complaint.full_name}"
    message = render_to_string("emails/complaint_notification.txt", context)
    sent = _send_email(subject, message, [admin_email])
    if complaint.email:
        confirm_subject = "Your FitZone complaint has been received"
        confirm_message = render_to_string("emails/complaint_confirmation.txt", {
            "full_name": complaint.full_name,
            "category": complaint.get_category_display(),
        })
        _send_email(confirm_subject, confirm_message, [complaint.email])
    return sent


def send_plan_assignment_email(plan, *, plan_type, client_member):
    if not plan or not client_member or not getattr(client_member, "user", None):
        return False
    user = client_member.user
    if not getattr(user, "email", None):
        return False
    context = {
        "user_name": user.get_full_name() or user.username,
        "coach_name": plan.coach.get_full_name() or plan.coach.username,
        "plan_type": plan_type,
        "goal": plan.goal if hasattr(plan, "goal") else plan.name,
        "plan_details": getattr(plan, "instructions", "") or getattr(plan, "exercise", "") or "",
        "dashboard_url": "http://localhost:8000/client-dashboard/",
    }
    subject = f"Your coach assigned a new {plan_type} plan"
    message = render_to_string("emails/plan_assignment_email.txt", context)
    return _send_email(subject, message, [user.email])


def send_payment_success_email(payment_order):
    if not payment_order or not getattr(payment_order, "user", None):
        return False
    user = payment_order.user
    if not getattr(user, "email", None):
        return False
    context = {
        "user_name": user.get_full_name() or user.username,
        "plan_name": payment_order.plan.name,
        "amount": payment_order.amount,
        "status": payment_order.status,
        "order_reference": payment_order.gateway_order_id,
        "payment_method": payment_order.payment_method or "Card/UPI",
        "date": payment_order.updated_at.date().isoformat(),
    }
    subject = "FitZone payment confirmation"
    message = render_to_string("emails/payment_success_email.txt", context)
    return _send_email(subject, message, [user.email])
