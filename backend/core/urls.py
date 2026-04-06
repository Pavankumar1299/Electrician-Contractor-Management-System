from django.urls import path
from . import views

urlpatterns = [
    # Pages
    path('', views.home_page, name='home'),
    path('dashboard/', views.dashboard_page, name='dashboard'),

    path('electricians/', views.electricians_view, name='electricians'),
    path('electricians/add/', views.add_electrician, name='add_electrician'),
    path('electricians/edit/<int:id>/', views.edit_electrician, name='edit_electrician'),
    path('electricians/delete/<int:id>/', views.delete_electrician, name='delete_electrician'),

    path('jobs/', views.jobs_page, name='jobs'),
    path('jobs/add/', views.add_job, name='add_job'),
    path('jobs/edit/<int:id>/', views.edit_job, name='edit_job'),
    path('jobs/delete/<int:id>/', views.delete_job, name='delete_job'),

    path('tasks/', views.tasks_page, name='tasks'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/edit/<int:id>/', views.edit_task, name='edit_task'),
    path('tasks/delete/<int:id>/', views.delete_task, name='delete_task'),

    path('materials/', views.materials_page, name='materials'),
    path('materials/add/', views.add_material, name='add_material'),
    path('materials/edit/<int:id>/', views.edit_material, name='edit_material'),
    path('materials/delete/<int:id>/', views.delete_material, name='delete_material'),

    path('profile/', views.profile_page, name='profile'),
    path('reports/', views.reports_page, name='reports'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # API
    path('api/dashboard/', views.dashboard_view, name='api_dashboard'),
    
    path('api/add-job/', views.add_job, name='api_add_job'),
    path('api/add-task/', views.add_task, name='api_add_task'),
]