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
from rest_framework_simplejwt.views import TokenObtainPairView
from django.urls import path
from . import views

urlpatterns = [
    # Pages
    path('', views.home_page),
    path('dashboard/', views.dashboard_page),
    path('electricians/', views.electricians_page),
    path('jobs/', views.jobs_page),
    path('tasks/', views.tasks_page),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/', views.login_page),

    # Auth
    # path('register/', views.register),
    # path('login/', views.login),
    path('logout/', views.logout),

    # API
    path('api/dashboard/', views.dashboard_api),
    path('api/add-electrician/', views.add_electrician),
    path('api/add-job/', views.add_job),
    path('api/add-task/', views.add_task),
]