from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profile

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="帳號或 Email")

    error_messages = {
        "invalid_login": "帳號/Email 或密碼錯誤，請再試一次。",
        "inactive": "此帳號已停用。",
    }

    def clean(self):
        identity = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if identity and password:
            username = identity
            if "@" in identity:
                matched_user = User.objects.filter(email__iexact=identity).first()
                if matched_user:
                    username = matched_user.username
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("bio", "dietary_preference", "avatar")
