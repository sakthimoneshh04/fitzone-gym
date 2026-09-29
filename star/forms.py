from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Complaint, DietPlan, Enquiry, MemberProfile, WorkoutCompletion, WorkoutPlan


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    role = forms.ChoiceField(
        label="Select Role",
        choices=(
            ("", "Select your role"),
            *sorted(MemberProfile.ROLE_CHOICES, key=lambda choice: choice[1]),
        ),
        widget=forms.Select,
    )
    phone = forms.CharField(max_length=15, required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "role", "phone", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            MemberProfile.objects.create(user=user, role=self.cleaned_data["role"], phone=self.cleaned_data["phone"])
        return user


class CalculatorForm(forms.Form):
    SEX_CHOICES = (("male", "Male"), ("female", "Female"))
    ACTIVITY_CHOICES = (("1.2", "Sedentary"), ("1.375", "Lightly active"), ("1.55", "Moderately active"), ("1.725", "Very active"), ("1.9", "Extra active"))
    age = forms.IntegerField(min_value=13, max_value=100)
    sex = forms.ChoiceField(choices=SEX_CHOICES)
    height_cm = forms.DecimalField(min_value=100, max_value=250, decimal_places=2, max_digits=6)
    weight_kg = forms.DecimalField(min_value=25, max_value=300, decimal_places=2, max_digits=6)
    activity = forms.ChoiceField(choices=ACTIVITY_CHOICES)


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("full_name", "email", "phone", "category", "description", "preferred_contact")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ("full_name", "email", "phone", "enquiry_type", "message")
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }


class DietPlanForm(forms.ModelForm):
    class Meta:
        model = DietPlan
        exclude = ("coach",)
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = MemberProfile.objects.filter(role="client").select_related("user")


class WorkoutPlanForm(forms.ModelForm):
    class Meta:
        model = WorkoutPlan
        exclude = ("coach",)
        widgets = {"workout_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = MemberProfile.objects.filter(role="client").select_related("user")


class ComplaintUpdateForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ("status", "response")
        widgets = {"response": forms.Textarea(attrs={"rows": 3})}


class EnquiryUpdateForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ("status", "response")
        widgets = {"response": forms.Textarea(attrs={"rows": 3})}


class WorkoutCompletionForm(forms.ModelForm):
    class Meta:
        model = WorkoutCompletion
        fields = ("status", "completed_on", "note")
        widgets = {"completed_on": forms.DateInput(attrs={"type": "date"}), "note": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("status") == "completed" and not cleaned_data.get("completed_on"):
            self.add_error("completed_on", "Add the completion date.")
        return cleaned_data