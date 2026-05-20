from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, FloatField, Q
from django.db.models.functions import Cast
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from cells.models import (
    TestSession,
    DiagnosticCaseSession,
    DiagnosticCase,
    DiagnosticCaseProgress,
    Level,
    UserLevelProgress,
)
from .models import StudentGroup, StudentProfile, User


def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Требуется авторизация.")

        if request.user.role not in [User.Roles.TEACHER, User.Roles.ADMIN]:
            return HttpResponseForbidden("Этот раздел доступен только преподавателю.")

        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@teacher_required
def teacher_dashboard(request):
    group_id = request.GET.get("group")
    search = request.GET.get("search", "").strip()
    groups = StudentGroup.objects.all()

    students_qs = (
        StudentProfile.objects
        .select_related("user", "group")
        .filter(user__role=User.Roles.STUDENT)
    )

    selected_group = None

    if group_id:
        selected_group = groups.filter(id=group_id).first()
        if selected_group:
            students_qs = students_qs.filter(group=selected_group)
    if search:
        students_qs = students_qs.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
        )
    student_users = User.objects.filter(
        id__in=students_qs.values("user_id")
    )

    completed_sessions = TestSession.objects.filter(
        user__in=student_users,
        status=TestSession.Status.COMPLETED,
        total_questions__gt=0,
    )

    diagnostic_sessions = DiagnosticCaseSession.objects.filter(
        user__in=student_users,
        status=DiagnosticCaseSession.Status.COMPLETED,
    )

    total_students = students_qs.count()
    total_tests_completed = completed_sessions.count()
    total_diagnostic_cases_completed = diagnostic_sessions.count()

    average_accuracy = completed_sessions.annotate(
        accuracy=Cast(F("correct_answers"), FloatField()) * 100.0 / Cast(F("total_questions"), FloatField())
    ).aggregate(
        value=Avg("accuracy")
    )["value"] or 0

    diagnostic_success_percent = 0
    if total_diagnostic_cases_completed:
        successful_diagnostic_cases = diagnostic_sessions.filter(
            counts_are_correct=True,
            diagnosis_is_correct=True,
        ).count()

        diagnostic_success_percent = round(
            successful_diagnostic_cases * 100 / total_diagnostic_cases_completed,
            1,
        )

    students_stats = []

    for profile in students_qs:
        user_sessions = completed_sessions.filter(user=profile.user)

        user_average_accuracy = user_sessions.annotate(
            accuracy=Cast(F("correct_answers"), FloatField()) * 100.0 / Cast(F("total_questions"), FloatField())
        ).aggregate(
            value=Avg("accuracy")
        )["value"] or 0

        user_diagnostic_sessions = diagnostic_sessions.filter(user=profile.user)

        students_stats.append(
            {
                "profile": profile,
                "tests_completed": user_sessions.count(),
                "average_accuracy": round(user_average_accuracy, 1),
                "diagnostic_cases_completed": user_diagnostic_sessions.count(),
                "diagnostic_cases_successful": user_diagnostic_sessions.filter(
                    counts_are_correct=True,
                    diagnosis_is_correct=True,
                ).count(),
            }
        )

    context = {
        "groups": groups,
        "selected_group": selected_group,
        "selected_group_id": int(group_id) if group_id and group_id.isdigit() else None,
        "search": search,
        "total_students": total_students,
        "total_tests_completed": total_tests_completed,
        "total_diagnostic_cases_completed": total_diagnostic_cases_completed,
        "average_accuracy": round(average_accuracy, 1),
        "diagnostic_success_percent": diagnostic_success_percent,
        "students_stats": students_stats,
    }

    return render(request, "teacher/dashboard.html", context)


@login_required
@teacher_required
def teacher_student_detail(request, student_id):
    profile = get_object_or_404(
        StudentProfile.objects.select_related("user", "group"),
        id=student_id,
        user__role=User.Roles.STUDENT,
    )

    student = profile.user

    test_sessions = (
        TestSession.objects
        .filter(user=student)
        .select_related("level")
        .order_by("-started_at")
    )

    completed_test_sessions = test_sessions.filter(
        status=TestSession.Status.COMPLETED,
        total_questions__gt=0,
    )

    diagnostic_sessions = (
        DiagnosticCaseSession.objects
        .filter(user=student)
        .select_related("case")
        .order_by("-started_at")
    )

    completed_diagnostic_sessions = diagnostic_sessions.filter(
        status=DiagnosticCaseSession.Status.COMPLETED,
    )

    test_rows = []
    tests_100_count = 0

    for session in test_sessions:
        accuracy = 0

        if session.total_questions:
            accuracy = round(
                session.correct_answers * 100 / session.total_questions,
                1,
            )

        if (
            session.status == TestSession.Status.COMPLETED
            and session.total_questions
            and session.correct_answers == session.total_questions
        ):
            tests_100_count += 1

        if session.mode == TestSession.Mode.LEVEL and session.level:
            title = f"Уровень {session.level.order}: {session.level.title}"
        elif session.mode == TestSession.Mode.RANDOM:
            title = "Random test"
        elif session.mode == TestSession.Mode.TRAINER:
            title = "Adaptive trainer"
        else:
            title = session.get_mode_display()

        test_rows.append(
            {
                "session": session,
                "title": title,
                "accuracy": accuracy,
            }
        )

    diagnostic_rows = []

    for session in diagnostic_sessions:
        is_successful = (
            session.status == DiagnosticCaseSession.Status.COMPLETED
            and session.counts_are_correct
            and session.diagnosis_is_correct
        )

        diagnostic_rows.append(
            {
                "session": session,
                "is_successful": is_successful,
            }
        )

    active_levels = Level.objects.filter(is_active=True).order_by("order")

    level_progress_map = {
        progress.level_id: progress
        for progress in UserLevelProgress.objects.filter(
            user=student,
            level__in=active_levels,
        ).select_related("level")
    }

    level_rows = []

    for level in active_levels:
        progress = level_progress_map.get(level.id)

        level_rows.append(
            {
                "level": level,
                "progress": progress,
                "completions_count": progress.completions_count if progress else 0,
                "best_score": progress.best_score if progress else 0,
                "last_score": progress.last_score if progress else 0,
                "is_unlocked": progress.is_unlocked if progress else False,
                "is_completed": progress.is_completed if progress else False,
                "completed_at": progress.completed_at if progress else None,
            }
        )

    active_cases = DiagnosticCase.objects.filter(is_active=True).order_by("id")

    case_progress_map = {
        progress.case_id: progress
        for progress in DiagnosticCaseProgress.objects.filter(
            user=student,
            case__in=active_cases,
        ).select_related("case")
    }

    diagnostic_progress_rows = []

    for case in active_cases:
        progress = case_progress_map.get(case.id)

        diagnostic_progress_rows.append(
            {
                "case": case,
                "progress": progress,
                "attempts_count": progress.attempts_count if progress else 0,
                "is_completed": progress.is_completed if progress else False,
                "last_attempt_at": progress.last_attempt_at if progress else None,
                "completed_at": progress.completed_at if progress else None,
            }
        )

    total_completed_tests = completed_test_sessions.count()

    average_accuracy = 0
    if total_completed_tests:
        accuracies = [
            session.correct_answers * 100 / session.total_questions
            for session in completed_test_sessions
            if session.total_questions
        ]
        average_accuracy = round(sum(accuracies) / len(accuracies), 1) if accuracies else 0

    context = {
        "profile": profile,
        "student": student,

        "test_rows": test_rows,
        "diagnostic_rows": diagnostic_rows,
        "level_rows": level_rows,
        "diagnostic_progress_rows": diagnostic_progress_rows,

        "total_test_sessions": test_sessions.count(),
        "total_completed_tests": total_completed_tests,
        "tests_100_count": tests_100_count,
        "average_accuracy": average_accuracy,

        "total_diagnostic_sessions": diagnostic_sessions.count(),
        "completed_diagnostic_sessions_count": completed_diagnostic_sessions.count(),
    }

    return render(request, "teacher/student_detail.html", context)