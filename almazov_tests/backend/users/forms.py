from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Логин или email",
        widget=forms.TextInput(attrs={
            "class": "auth-input",
            "placeholder": "Введите логин или email",
            "autocomplete": "username",
        }),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            "class": "auth-input",
            "placeholder": "Введите пароль",
            "autocomplete": "current-password",
        }),
    )


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email")

    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(attrs={
            "class": "auth-input",
            "placeholder": "Придумайте логин",
            "autocomplete": "username",
        }),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "auth-input",
            "placeholder": "Введите email",
            "autocomplete": "email",
        }),
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            "class": "auth-input",
            "placeholder": "Введите пароль",
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={
            "class": "auth-input",
            "placeholder": "Повторите пароль",
            "autocomplete": "new-password",
        }),
    )