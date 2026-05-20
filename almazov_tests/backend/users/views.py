from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.db import transaction

from .forms import CustomUserCreationForm
from .models import StudentProfile
from django.shortcuts import redirect

from .models import User


def role_based_redirect(request):
    if request.user.role in [User.Roles.TEACHER, User.Roles.ADMIN]:
        return redirect("teacher_dashboard")

    return redirect("dashboard")

def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.role = user.Roles.STUDENT
                user.save()

                StudentProfile.objects.create(
                    user=user,
                    group=form.cleaned_data["group"],
                )

            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()

    return render(request, "auth/register.html", {"form": form})