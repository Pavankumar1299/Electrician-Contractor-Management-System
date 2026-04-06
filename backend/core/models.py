from django.db import models

class Electrician(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    experience = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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