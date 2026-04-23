from django.contrib import admin

from .models import (
    Cell,
    CellImage,
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
    list_display = ("order", "title", "badge", "required_completions", "question_count", "is_active")
    list_filter = ("badge", "is_active")
    inlines = [LevelCellInline]


@admin.register(UserLevelProgress)
class UserLevelProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "completions_count", "best_score", "is_unlocked")
    list_filter = ("is_unlocked", "level")


admin.site.register(Cell)
admin.site.register(LevelCell)
admin.site.register(CellImage)
admin.site.register(TestSession)
admin.site.register(TestSessionImage)
admin.site.register(UserImageAnswer)
admin.site.register(UserImagePerformance)
admin.site.register(ImageSimilarity)
admin.site.register(GlobalImageStats)