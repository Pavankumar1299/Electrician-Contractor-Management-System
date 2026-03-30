"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

urlpatterns = [
    # Pages
    path('', views.home_page, name='home'),
    path('dashboard/', views.dashboard_page, name='dashboard'),  # <-- Fixed!
    path('electricians/', views.electricians_page, name='electricians'),
    path('jobs/', views.jobs_page, name='jobs'),
    path('tasks/', views.tasks_page, name='tasks'),
    path('materials/', views.materials_page, name='materials'),
    path('profile/', views.profile_page, name='profile'),
    path('reports/', views.reports_page, name='reports'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # API
    path('api/dashboard/', views.dashboard_api, name='api_dashboard'),
    path('api/add-electrician/', views.add_electrician, name='api_add_electrician'),
    path('api/add-job/', views.add_job, name='api_add_job'),
    path('api/add-task/', views.add_task, name='api_add_task'),
]