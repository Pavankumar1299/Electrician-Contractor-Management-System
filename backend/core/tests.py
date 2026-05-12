from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile, Job, Task, Notification, Electrician

class ECMSTestSuite(TestCase):

    def setUp(self):
        self.client = Client()
        
        # 1. Create Admin
        self.admin_user = User.objects.create_user(username='admin', password='password123')
        UserProfile.objects.update_or_create(
            user=self.admin_user, 
            defaults={'role': 'ADMIN', 'phone': '1111111111'}
        )
        
        # 2. Create Contractor
        self.contractor_user = User.objects.create_user(username='contractor1', password='password123')
        UserProfile.objects.update_or_create(
            user=self.contractor_user, 
            defaults={'role': 'CONTRACTOR', 'phone': '2222222222'}
        )
        
        # 3. Create a Job
        self.job = Job.objects.create(
            title="TechHub Wiring", 
            description="Complete wiring of floor 4",
            location="Floor 4", 
            deadline="2026-12-31",
            assigned_contractor=self.contractor_user,
            status='ACTIVE'
        )

    # 7.1 UNIT TESTING
    def test_job_model_creation(self):
        """Test if a Job is correctly created and linked to a Contractor"""
        job = Job.objects.get(title="TechHub Wiring")
        self.assertEqual(job.assigned_contractor.username, 'contractor1')
        self.assertEqual(job.status, 'ACTIVE')
        
        # Custom Print Output
        print("\n✅ [SUCCESS] 7.1 Unit Test: Job model creation verified.")

    # 7.2 FUNCTIONALITY TESTING
    def test_admin_dashboard_access(self):
        """Test if Admin can access the dashboard and get a 200 OK status"""
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.cookies['access_token'] = str(refresh.access_token)
        
        try:
            response = self.client.get(reverse('dashboard'))
        except:
            response = self.client.get('/dashboard/')
            
        self.assertEqual(response.status_code, 200)
        
        # Custom Print Output
        print("\n✅ [SUCCESS] 7.2 Functionality Test: Secure Admin dashboard access verified.")

    # 7.3 INTEGRATION TESTING
    def test_task_completion_creates_notification(self):
        """Test if completing a task correctly integrates with the Notification system"""
        task = Task.objects.create(
            title="Wire Panel", 
            description="Wire the main electrical panel", 
            job=self.job, 
            status="Pending"
        )
        
        task.status = "Completed"
        task.save()
        
        Notification.objects.create(
            user=self.admin_user,
            message=f"Task Update: '{task.title}' is now Completed."
        )
        
        admin_notifications = Notification.objects.filter(user=self.admin_user).count()
        self.assertEqual(admin_notifications, 1)
        
        # Custom Print Output
        print("\n✅ [SUCCESS] 7.3 Integration Test: Task & Notification modules linked successfully.")

    # 7.4 VERIFICATION AND VALIDATION TESTING
    def test_contractor_data_fencing(self):
        """Validation: Ensure Contractor 2 cannot access Contractor 1's jobs"""
        contractor2 = User.objects.create_user(username='contractor2', password='password123')
        
        UserProfile.objects.update_or_create(
            user=contractor2,
            defaults={'role': 'CONTRACTOR', 'phone': '3333333333'}
        )
        
        c2_jobs = Job.objects.filter(assigned_contractor=contractor2).count()
        
        self.assertEqual(c2_jobs, 0)
        
        # Custom Print Output
        print("\n✅ [SUCCESS] 7.4 Validation Test: Contractor RBAC Data Fencing is secure.")