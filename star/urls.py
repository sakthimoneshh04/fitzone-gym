from django.urls import path
from . import views

urlpatterns = [
    path("",views.index,name="index"),
    path("about/",views.about,name="about"),
    path("services/",views.services,name="services"),
    path("complaint/", views.complaint, name="complaint"),
    path("enquiry/", views.enquiry, name="enquiry"),
    path("contact/",views.contact,name="contact"),
    path("subscriptions/", views.subscription_plans, name="subscription_plans"),
    path("payments/create-order/", views.create_payment_order, name="create_payment_order"),
    path("payments/verify/", views.verify_payment, name="verify_payment"),
    path("payments/failed/", views.payment_failed, name="payment_failed"),
    path("payments/webhook/", views.payment_webhook, name="payment_webhook"),

    path("choose-role/",views.choose_role,name="choose_role"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("coach-dashboard/",views.coach_dashboard,name="coach_dashboard"),
    path("client-dashboard/",views.client_dashboard,name="client_dashboard"),
    path("coach/diet/create/", views.coach_diet_create, name="coach_diet_create"),
    path("coach/diet/<int:pk>/edit/", views.coach_diet_edit, name="coach_diet_edit"),
    path("coach/diet/<int:pk>/delete/", views.coach_diet_delete, name="coach_diet_delete"),
    path("coach/workout/create/", views.coach_workout_create, name="coach_workout_create"),
    path("coach/workout/<int:pk>/edit/", views.coach_workout_edit, name="coach_workout_edit"),
    path("coach/workout/<int:pk>/delete/", views.coach_workout_delete, name="coach_workout_delete"),
    path("coach/complaint/<int:pk>/update/", views.coach_complaint_update, name="coach_complaint_update"),
    path("coach/enquiry/<int:pk>/update/", views.coach_enquiry_update, name="coach_enquiry_update"),
    path("calculators/<str:calculator_type>/", views.calculator, name="calculator"),
    path("logout/",views.logout_view, name="logout"),
]