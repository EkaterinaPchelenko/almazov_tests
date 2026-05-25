from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.urls import path, reverse_lazy
from django.urls import path

from .forms import CustomAuthenticationForm
from .teacher_views import teacher_dashboard, teacher_student_detail
from .views import register_view, role_based_redirect, confirm_email_view
urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="auth/login.html",
            authentication_form=CustomAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "teacher/students/<int:student_id>/",
        teacher_student_detail,
        name="teacher_student_detail",
    ),

    path(
        "password-reset/",
        PasswordResetView.as_view(
            template_name="auth/password_reset.html",
            email_template_name="auth/password_reset_email.txt",
            html_email_template_name="auth/password_reset_email.html",
            subject_template_name="auth/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        PasswordResetDoneView.as_view(
            template_name="auth/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="auth/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        PasswordResetCompleteView.as_view(
            template_name="auth/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("after-login/", role_based_redirect, name="after_login"),
    path("teacher/dashboard/", teacher_dashboard, name="teacher_dashboard"),
    path("register/", register_view, name="register"),
    path("confirm-email/<path:token>/", confirm_email_view, name="confirm_email"),
    path("logout/", LogoutView.as_view(), name="logout"),
]