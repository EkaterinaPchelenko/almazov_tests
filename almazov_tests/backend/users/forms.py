from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Логин или email",
        widget=forms.TextInput(
            attrs={
                "class": "auth-input",
                "placeholder": "student@university.edu",
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Введите пароль",
                "autocomplete": "current-password",
            }
        ),
    )


class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Придумайте логин",
                "autocomplete": "username",
            }
        ),
    )

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "placeholder": "student@university.edu",
                "autocomplete": "email",
            }
        ),
    )

    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Минимум 8 символов",
                "autocomplete": "new-password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "placeholder": "Повторите пароль",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email")