from django.db import models

# class User(models.Model):
#     name = models.CharField(max_length=100)
#     email = models.EmailField(unique=True)
#     password = models.CharField(max_length=100)

#     def __str__(self):
#         return self.email


class Electrician(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    experience = models.IntegerField()

    def __str__(self):
        return self.name


class Job(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    electrician = models.ForeignKey(Electrician, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class Task(models.Model):
    title = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)

    def __str__(self):
        return self.title