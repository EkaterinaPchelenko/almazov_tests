from django.contrib import admin
from django.urls import path
from cells import views as cell_views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", cell_views.dashboard, name="dashboard"),

    path("test/random/", cell_views.start_test_random, name="start_test_random"),
    path("test/question/", cell_views.get_question, name="get_question"),

    path('test/submit/', cell_views.submit_answer, name='submit_answer'),

    path('test/result/', cell_views.test_result, name='test_result'),
    path("test/<str:mode>/", cell_views.start_test, name="start_test"),

]