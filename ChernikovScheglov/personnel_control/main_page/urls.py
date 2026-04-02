from . import views
from django.urls import path


app_name = 'main_page'

urlpatterns = [
    path('', views.main_page, name='main_page'),  # Главная страница
    path('login/', views.login, name='login'), # Страница авторизации
    path('registration/', views.registration, name='registration'),  # Страница регистрации
    path('about/', views.about, name='about'),  # Страница "Подробно"
]