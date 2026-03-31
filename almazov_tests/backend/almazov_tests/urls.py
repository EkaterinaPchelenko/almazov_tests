from django.contrib import admin
from django.urls import path
from cells import views as cell_views
from users.views import UserLoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", cell_views.dashboard, name="dashboard"),
    path("login/", UserLoginView.as_view(), name="login"),

    path("test/<str:mode>/start/", cell_views.start_test, name="start_test"),
    path("test/<int:session_id>/", cell_views.test_page, name="test_page"),
    path("test/<int:session_id>/submit/", cell_views.submit_answer, name="submit_answer"),
]