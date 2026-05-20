from django.contrib import admin

from .models import User, StudentProfile, StudentGroup


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "role", "is_staff", "is_active")
    search_fields = ("email", "username")
    list_filter = ("role", "is_staff", "is_active")


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ("number",)
    search_fields = ("number",)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "group", "overall_accuracy", "total_tests_passed")
    search_fields = ("user__email", "user__username", "group__number")
    list_filter = ("group",)