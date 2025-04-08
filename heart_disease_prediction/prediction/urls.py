from django.urls import path
from .views import home_view, custom_login, dashboard_view, register_view, predict_heart_disease_from_pdf, health_check_view, daily_check_view, download_history, clear_history, recommendations_view
from django.contrib.auth import views as auth_views
urlpatterns = [
    path("", home_view, name='home'),
    path('login/', custom_login, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path("register/", register_view, name="register"),
    # path("health-check/", health_check, name="health_check"),
    path("healthcheck/", health_check_view, name="health_check"),
    path("predict/upload/", predict_heart_disease_from_pdf, name="predict"),
    path('dailycheck/', daily_check_view, name='daily_check'),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path('predict/history/download/', download_history, name='download_history'),
    path('predict/history/clear/', clear_history, name='clear_history'),
    path('recommend/', recommendations_view, name='recommend'),
]
