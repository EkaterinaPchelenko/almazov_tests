from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import CustomAuthenticationForm
from .views import register_view
from .teacher_views import teacher_dashboard, teacher_student_detail
from .views import register_view, role_based_redirect

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
    path("after-login/", role_based_redirect, name="after_login"),
    path("teacher/dashboard/", teacher_dashboard, name="teacher_dashboard"),
    path("register/", register_view, name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
]