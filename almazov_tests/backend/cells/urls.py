from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("levels/", views.levels_page, name="levels_page"),
    path("levels/<int:level_id>/start/", views.start_level_test, name="start_level_test"),

    path("test/start/<str:mode>/", views.start_test, name="start_test"),
    path("test/<int:session_id>/", views.test_page, name="test_page"),
    path("test/<int:session_id>/question/", views.test_question_partial, name="test_question_partial"),
    path("test/<int:session_id>/submit/", views.submit_answer_htmx, name="submit_answer_htmx"),
]