from django.shortcuts import render
from django.contrib.auth.views import LoginView


class UserLoginView(LoginView):
    template_name = "users/login.html"
# Create your views here.
