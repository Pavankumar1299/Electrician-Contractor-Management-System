from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import User, Electrician, Job, Task
import json
from django.views.decorators.csrf import csrf_exempt
<<<<<<< HEAD
from django.shortcuts import render

def login_page(request):
    return render(request, 'login.html')
=======

>>>>>>> 76153a2364c5b2ada1e11581726e99d53f9e84a6

# -------------------- PAGE VIEWS (HTML) --------------------

def home_page(request):
    return render(request, "index.html")


def dashboard_page(request):

    # protect route
    # if not request.session.get('user'):
    #     return redirect("/")

    return render(request, "dashboard.html")


def electricians_page(request):

    # if not request.session.get('user'):
    #     return redirect("/")

    return render(request, "electricians.html")


def jobs_page(request):

    # if not request.session.get('user'):
    #     return redirect("/")

    return render(request, "jobs.html")


def tasks_page(request):

    # if not request.session.get('user'):
    #     return redirect("/")

    return render(request, "tasks.html")


# -------------------- AUTH (HTML FLOW) --------------------

    # type your code here



# ---------------- LOGOUT ----------------
def logout(request):
    request.session.flush()
    return redirect("/")


# -------------------- API (JSON for fetch/Postman) --------------------

def dashboard_api(request):
    electricians = list(Electrician.objects.values())
    jobs = list(Job.objects.values())
    tasks = list(Task.objects.values())

    return JsonResponse({
        "electricians": electricians,
        "jobs": jobs,
        "tasks": tasks
    })


@csrf_exempt
def add_electrician(request):
    if request.method == "POST":
        data = json.loads(request.body)

        Electrician.objects.create(
            name=data.get("name"),
            phone=data.get("phone"),
            experience=data.get("experience")
        )

        return JsonResponse({"message": "Electrician added"})


@csrf_exempt
def add_job(request):
    if request.method == "POST":
        data = json.loads(request.body)

        electrician = Electrician.objects.get(id=data.get("electrician_id"))

        Job.objects.create(
            title=data.get("title"),
            description=data.get("description"),
            electrician=electrician
        )

        return JsonResponse({"message": "Job added"})


@csrf_exempt
def add_task(request):
    if request.method == "POST":
        data = json.loads(request.body)

        job = Job.objects.get(id=data.get("job_id"))

        Task.objects.create(
            title=data.get("title"),
            status=data.get("status"),
            job=job
        )

        return JsonResponse({"message": "Task added"})