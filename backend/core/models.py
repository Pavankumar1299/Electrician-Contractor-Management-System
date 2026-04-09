from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --------------------- USER PROFILES --------------------
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('CONTRACTOR', 'Contractor'),
        ('ELECTRICIAN', 'Electrician'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
# - Automatically create UserProfile when a new User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, role='ELECTRICIAN')

# ----------------------- NOTIFICATIONS --------------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

# --------------------- ELECTRICIANS --------------------
class Electrician(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    experience = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# --------------------- JOBS --------------------
class Job(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    deadline = models.DateField()

    electrician = models.ForeignKey(
        Electrician,
        on_delete=models.SET_NULL,
        null=True,
        related_name="jobs"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# --------------------- TASKS --------------------
class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="tasks"
    )

    electrician = models.ForeignKey(
        Electrician,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tasks"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
# --------------------- MATERIALS --------------------
class Material(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=50)  # kg, pcs, meters

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="materials"
    )

    used_quantity = models.IntegerField(default=0)

    def __str__(self):
        return self.name
    
    @property
    def remaining(self):
        return self.quantity - self.used_quantity