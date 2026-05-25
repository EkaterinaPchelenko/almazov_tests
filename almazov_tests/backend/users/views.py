from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import CustomUserCreationForm
from .models import StudentProfile, User


EMAIL_CONFIRMATION_SALT = "users.email.confirmation"


def role_based_redirect(request):
    if request.user.role in [User.Roles.TEACHER, User.Roles.ADMIN]:
        return redirect("teacher_dashboard")
    return redirect("dashboard")


def make_email_confirmation_token(user):
    signer = TimestampSigner(salt=EMAIL_CONFIRMATION_SALT)
    return signer.sign(str(user.pk))


def send_confirmation_email(request, user):
    token = make_email_confirmation_token(user)

    confirm_url = request.build_absolute_uri(
        reverse("confirm_email", kwargs={"token": token})
    )

    subject = "Подтверждение регистрации | Medical Cell Trainer"

    message = (
        f"Здравствуйте, {user.first_name}!\n\n"
        "Для завершения регистрации подтвердите email по ссылке:\n"
        f"{confirm_url}\n\n"
        "Если вы не регистрировались в системе, просто проигнорируйте это письмо."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def register_view(request):
    if request.user.is_authenticated:
        return role_based_redirect(request)

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.role = User.Roles.STUDENT
                user.is_active = False
                user.save()

                StudentProfile.objects.create(
                    user=user,
                    group=form.cleaned_data["group"],
                )

                send_confirmation_email(request, user)

            return render(
                request,
                "auth/registration_pending.html",
                {"email": user.email},
            )
    else:
        form = CustomUserCreationForm()

    return render(request, "auth/register.html", {"form": form})


def confirm_email_view(request, token):
    signer = TimestampSigner(salt=EMAIL_CONFIRMATION_SALT)

    try:
        user_pk = signer.unsign(token, max_age=60 * 60 * 24)
    except SignatureExpired:
        messages.error(request, "Ссылка подтверждения устарела. Зарегистрируйтесь заново.")
        return redirect("register")
    except BadSignature:
        messages.error(request, "Некорректная ссылка подтверждения.")
        return redirect("register")

    user = get_object_or_404(User, pk=user_pk)

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])

    login(
        request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )

    messages.success(request, "Email подтверждён. Регистрация завершена.")
    return role_based_redirect(request)