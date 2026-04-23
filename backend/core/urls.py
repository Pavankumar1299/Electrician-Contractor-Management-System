from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
# Home
    path('', views.home_page, name='home'),

# Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

# Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

# Contractors
    path('contractors/', views.contractors_view, name='contractors'),
    path('contractors/add/', views.add_contractor, name='add_contractor'),
    path('contractors/edit/<int:id>/', views.edit_contractor, name='edit_contractor'),
    path('contractors/delete/<int:id>/', views.delete_contractor, name='delete_contractor'),

# Electricians
    path('electricians/', views.electricians_view, name='electricians'),
    path('electricians/add/', views.add_electrician, name='add_electrician'),
    path('electricians/edit/<int:id>/', views.edit_electrician, name='edit_electrician'),
    path('electricians/delete/<int:id>/', views.delete_electrician, name='delete_electrician'),

# Jobs
    path('jobs/', views.jobs_page, name='jobs'),
    path('jobs/add/', views.add_job, name='add_job'),
    path('jobs/edit/<int:id>/', views.edit_job, name='edit_job'),
    path('jobs/delete/<int:id>/', views.delete_job, name='delete_job'),

# Tasks
    path('tasks/', views.tasks_page, name='tasks'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/edit/<int:id>/', views.edit_task, name='edit_task'),
    path('tasks/delete/<int:id>/', views.delete_task, name='delete_task'),

# Materials
    path('materials/', views.materials_page, name='materials'),
    path('materials/add/', views.add_material, name='add_material'),
    path('materials/edit/<int:id>/', views.edit_material, name='edit_material'),
    path('materials/delete/<int:id>/', views.delete_material, name='delete_material'),

# Reports
    path('reports/', views.reports_page, name='reports'),

# Profile
    path('profile/', views.profile_page, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),

# Notifications
    path('notifications/', views.notifications_page, name='notifications'),
    path('notifications/read/<int:id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notification/delete/<int:id>/', views.delete_notification, name='delete_notification'),

# Admin - View As
    path('contractors/view-as/<int:id>/', views.view_as_contractor, name='view_as_contractor'),
    path('electricians/view-as/<int:id>/', views.view_as_user, name='view_as_user'),
    path('stop-viewing-as/', views.stop_viewing_as, name='stop_viewing_as'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)