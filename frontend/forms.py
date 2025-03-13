from django import forms
from django.core.exceptions import ValidationError

from fedletic.models import FedleticUser


class LoginForm(forms.Form):
    username = forms.EmailField(
        max_length=64,
        required=True,
        label="email",
    )
    password = forms.CharField(
        required=True, min_length=8, max_length=64, widget=forms.PasswordInput()
    )


class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=64,
        required=True,
    )
    email = forms.EmailField(
        required=True,
    )
    password = forms.CharField(
        required=True, min_length=8, max_length=64, widget=forms.PasswordInput()
    )

    def clean_username(self):
        desired_username = self.cleaned_data["username"]
        if FedleticUser.objects.filter(username=desired_username).exists():
            raise ValidationError("Username already exists")

        return desired_username

    def clean_email(self):
        desired_email = self.cleaned_data["email"]
        if FedleticUser.objects.filter(email=desired_email).exists():
            raise ValidationError("Email already in use")
        return desired_email
