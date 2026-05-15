from django.contrib import admin

from .models import (
    Cell,
    CellImage,
    DiagnosticCase,
    DiagnosticCaseExpectedCount,
    DiagnosticCaseExpectedFinding,
    DiagnosticCaseFindingAnswer,
    DiagnosticCaseImage,
    DiagnosticCaseImageAnswer,
    DiagnosticCaseProgress,
    DiagnosticCaseSession,
    DiagnosticFinding,
    GlobalImageStats,
    ImageSimilarity,
    Level,
    LevelCell,
    TestSession,
    TestSessionImage,
    UserImageAnswer,
    UserImagePerformance,
    UserLevelProgress,
)


class LevelCellInline(admin.TabularInline):
    model = LevelCell
    extra = 1


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "title",
        "question_type",
        "badge",
        "required_completions",
        "question_count",
        "is_active",
    )
    list_filter = ("badge", "is_active")
    inlines = [LevelCellInline]


@admin.register(UserLevelProgress)
class UserLevelProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "completions_count", "best_score", "is_unlocked")
    list_filter = ("is_unlocked", "level")


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    search_fields = ("name", "latin_name")


@admin.register(DiagnosticFinding)
class DiagnosticFindingAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


class DiagnosticCaseExpectedCountInline(admin.TabularInline):
    model = DiagnosticCaseExpectedCount
    extra = 1
    autocomplete_fields = ("cell",)


class DiagnosticCaseExpectedFindingInline(admin.TabularInline):
    model = DiagnosticCaseExpectedFinding
    extra = 1
    autocomplete_fields = ("finding",)


class DiagnosticCaseImageInline(admin.TabularInline):
    model = DiagnosticCaseImage
    extra = 1


@admin.register(DiagnosticCase)
class DiagnosticCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "diagnosis", "is_active")
    list_filter = ("diagnosis", "is_active")
    search_fields = ("title", "diagnosis", "note")
    inlines = [
        DiagnosticCaseExpectedCountInline,
        DiagnosticCaseExpectedFindingInline,
        DiagnosticCaseImageInline,
    ]


@admin.register(DiagnosticCaseProgress)
class DiagnosticCaseProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "case",
        "is_completed",
        "attempts_count",
        "last_attempt_at",
        "completed_at",
    )
    list_filter = ("is_completed", "case")


@admin.register(DiagnosticCaseSession)
class DiagnosticCaseSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "case",
        "status",
        "current_offset",
        "counts_are_correct",
        "diagnosis_is_correct",
        "selected_diagnosis",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "counts_are_correct", "diagnosis_is_correct", "case")


@admin.register(DiagnosticCaseImageAnswer)
class DiagnosticCaseImageAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "case_image", "selected_cell", "created_at")
    list_filter = ("selected_cell",)
    autocomplete_fields = ("selected_cell",)


@admin.register(DiagnosticCaseFindingAnswer)
class DiagnosticCaseFindingAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "finding", "selected_count")
    list_filter = ("finding",)
    search_fields = ("finding__title", "session__case__title")
    autocomplete_fields = ("finding",)


admin.site.register(LevelCell)
admin.site.register(CellImage)
admin.site.register(TestSession)
admin.site.register(TestSessionImage)
admin.site.register(UserImageAnswer)
admin.site.register(UserImagePerformance)
admin.site.register(ImageSimilarity)
admin.site.register(GlobalImageStats)