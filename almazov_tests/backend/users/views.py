from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import CustomUserCreationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            return redirect("dashboard")
    else:
        form = CustomUserCreationForm()

    return render(request, "auth/register.html", {"form": form})