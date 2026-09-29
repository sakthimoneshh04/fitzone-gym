import json
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CalculatorRecord, MemberProfile, PaymentOrder, Plan, Subscription


class MemberAuthenticationTests(TestCase):
	def register(self, username="client", role="client"):
		return self.client.post(reverse("register"), {
			"username": username,
			"first_name": "Test",
			"last_name": "Member",
			"email": f"{username}@example.com",
			"role": role,
			"phone": "5551234",
			"password1": "StrongPassword123!",
			"password2": "StrongPassword123!",
		})

	def test_registration_creates_user_and_profile(self):
		response = self.register()
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response["Location"], reverse("dashboard"))
		user = User.objects.get(username="client")
		self.assertTrue(user.check_password("StrongPassword123!"))
		self.assertEqual(user.member_profile.role, "client")

	@override_settings(ADMIN_EMAIL="admin@example.com", DEFAULT_FROM_EMAIL="noreply@example.com")
	@patch("star.email_service.send_mail")
	def test_successful_login_sends_one_notification(self, mock_send):
		user = User.objects.create_user(
			username="login-user",
			email="login-user@example.com",
			password="StrongPassword123!",
		)
		MemberProfile.objects.create(user=user, role="client")

		response = self.client.post(reverse("login"), {
			"username": "login-user",
			"password": "StrongPassword123!",
		})

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response["Location"], reverse("dashboard"))
		mock_send.assert_called_once()
		self.assertEqual(mock_send.call_args.args[0], "New User Login - FitZone Gym")
		self.assertIn("Username: login-user", mock_send.call_args.args[1])
		self.assertEqual(mock_send.call_args.args[3], ["admin@example.com"])
		self.assertFalse(mock_send.call_args.kwargs["fail_silently"])

	@patch("star.email_service.send_mail")
	def test_failed_login_does_not_send_notification(self, mock_send):
		User.objects.create_user(username="login-user", password="StrongPassword123!")

		response = self.client.post(reverse("login"), {
			"username": "login-user",
			"password": "wrong-password",
		})

		self.assertEqual(response.status_code, 200)
		mock_send.assert_not_called()

	@patch("star.email_service.send_mail", side_effect=RuntimeError("SMTP unavailable"))
	def test_login_succeeds_when_notification_fails(self, mock_send):
		user = User.objects.create_user(username="login-user", password="StrongPassword123!")
		MemberProfile.objects.create(user=user, role="client")

		response = self.client.post(reverse("login"), {
			"username": "login-user",
			"password": "StrongPassword123!",
		})

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response["Location"], reverse("dashboard"))
		mock_send.assert_called_once()

	def test_role_protects_other_dashboard(self):
		self.register()
		response = self.client.get(reverse("coach_dashboard"))
		self.assertRedirects(response, reverse("client_dashboard"))

	def test_logout_requires_post_and_clears_authentication(self):
		self.register()
		self.assertEqual(self.client.get(reverse("logout")).status_code, 302)
		self.assertTrue(response := self.client.post(reverse("logout")))
		self.assertRedirects(response, reverse("index"))
		self.assertFalse(response.wsgi_request.user.is_authenticated)

	def test_calculator_record_belongs_to_authenticated_user(self):
		self.register()
		response = self.client.post(reverse("calculator", args=["macro"]), {
			"age": 30,
			"sex": "male",
			"height_cm": "180",
			"weight_kg": "80",
			"activity": "1.55",
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(CalculatorRecord.objects.filter(user__username="client").count(), 1)


class PaymentFlowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="buyer", email="buyer@example.com", password="StrongPassword123!")
		MemberProfile.objects.create(user=self.user, role="client")
		self.client.force_login(self.user)
		self.plan = Plan.objects.create(
			name="Test Plan", slug="test-plan", price="100.00", duration_days=30, features=[]
		)

	@patch("star.email_service.send_mail")
	def test_successful_payment_sends_confirmation_email(self, mock_send):
		gateway = Mock()
		gateway.order.create.return_value = {"id": "order_test_123"}
		gateway.utility.verify_payment_signature.return_value = None
		gateway.payment.fetch.return_value = {
			"order_id": "order_test_123",
			"amount": 10000,
			"currency": "INR",
			"status": "captured",
			"method": "upi",
		}
		with patch("star.views._payment_client", return_value=gateway):
			order_response = self.client.post(reverse("create_payment_order"), {"plan_id": self.plan.pk})
			self.assertEqual(order_response.status_code, 200)
			response = self.client.post(
				reverse("verify_payment"),
				data=json.dumps({
					"razorpay_order_id": "order_test_123",
					"razorpay_payment_id": "pay_test_123",
					"razorpay_signature": "verified_signature",
				}),
				content_type="application/json",
			)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(mock_send.called)
		self.assertIn("payment confirmation", mock_send.call_args[0][0].lower())

	def test_order_uses_database_plan_amount_and_verifies_before_activation(self):
		gateway = Mock()
		gateway.order.create.return_value = {"id": "order_test_123"}
		gateway.utility.verify_payment_signature.return_value = None
		gateway.payment.fetch.return_value = {
			"order_id": "order_test_123",
			"amount": 10000,
			"currency": "INR",
			"status": "captured",
			"method": "upi",
		}
		with patch("star.views._payment_client", return_value=gateway):
			order_response = self.client.post(reverse("create_payment_order"), {"plan_id": self.plan.pk})
			self.assertEqual(order_response.status_code, 200)
			self.assertEqual(order_response.json()["amount"], 10000)
			payment = PaymentOrder.objects.get(gateway_order_id="order_test_123")
			self.assertEqual(payment.status, "pending")
			self.assertEqual(payment.currency, "INR")

			verify_response = self.client.post(
				reverse("verify_payment"),
				data=json.dumps({
					"razorpay_order_id": "order_test_123",
					"razorpay_payment_id": "pay_test_123",
					"razorpay_signature": "verified_signature",
				}),
				content_type="application/json",
			)

		self.assertEqual(verify_response.status_code, 200)
		self.assertTrue(verify_response.json()["success"])
		payment.refresh_from_db()
		self.assertEqual(payment.status, "paid")
		self.assertEqual(payment.payment_method, "upi")
		self.assertEqual(payment.gateway_signature, "verified_signature")
		self.assertEqual(Subscription.objects.get(payment_order=payment).status, "active")

	def test_amount_mismatch_does_not_activate_subscription(self):
		payment = PaymentOrder.objects.create(
			user=self.user, plan=self.plan, amount=self.plan.price, currency="INR", gateway_order_id="order_test_456"
		)
		gateway = Mock()
		gateway.utility.verify_payment_signature.return_value = None
		gateway.payment.fetch.return_value = {
			"order_id": "order_test_456", "amount": 20000, "currency": "INR", "status": "captured", "method": "upi"
		}
		with patch("star.views._payment_client", return_value=gateway):
			response = self.client.post(
				reverse("verify_payment"),
				data=json.dumps({
					"razorpay_order_id": payment.gateway_order_id,
					"razorpay_payment_id": "pay_test_456",
					"razorpay_signature": "verified_signature",
				}),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 400)
		self.assertFalse(Subscription.objects.filter(payment_order=payment).exists())

	def test_uncaptured_payment_does_not_activate_subscription(self):
		payment = PaymentOrder.objects.create(
			user=self.user, plan=self.plan, amount=self.plan.price, gateway_order_id="order_test_456"
		)
		gateway = Mock()
		gateway.utility.verify_payment_signature.return_value = None
		gateway.payment.fetch.return_value = {
			"order_id": "order_test_456", "amount": 10000, "currency": "INR", "status": "authorized"
		}
		with patch("star.views._payment_client", return_value=gateway):
			response = self.client.post(
				reverse("verify_payment"),
				data=json.dumps({
					"razorpay_order_id": payment.gateway_order_id,
					"razorpay_payment_id": "pay_test_456",
					"razorpay_signature": "verified_signature",
				}),
				content_type="application/json",
			)

		self.assertEqual(response.status_code, 400)
		self.assertFalse(Subscription.objects.filter(payment_order=payment).exists())

	@patch("star.email_service.send_mail")
	def test_registration_sends_welcome_email(self, mock_send):
		response = self.client.post(reverse("register"), {
			"username": "newmember",
			"first_name": "New",
			"last_name": "Member",
			"email": "newmember@example.com",
			"role": "client",
			"phone": "5551234",
			"password1": "StrongPassword123!",
			"password2": "StrongPassword123!",
		})
		self.assertEqual(response.status_code, 302)
		self.assertTrue(mock_send.called)
		self.assertIn("welcome to fitzone gym", mock_send.call_args[0][0].lower())
