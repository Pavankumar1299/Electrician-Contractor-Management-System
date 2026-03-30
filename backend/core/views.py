from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Electrician, Job, Task # Removed User from here to use default auth User
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
import json
from functools import wraps

# -------------------- SECURITY DECORATOR --------------------
# Place @jwt_cookie_required above any view that needs login protection
def jwt_cookie_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        token = request.COOKIES.get('access_token')
        if not token:
            return redirect('login')
        
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            request.user = jwt_auth.get_user(validated_token) # Attach user to request
        except (InvalidToken, AuthenticationFailed):
            # Token is expired or tampered with
            response = redirect('login')
            response.delete_cookie('access_token')
            return response
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# -------------------- PAGE VIEWS (HTML) --------------------

def home_page(request):
    return render(request, "index.html")

@jwt_cookie_required
def dashboard_page(request):
    # This page is now locked down!
    return render(request, "dashboard.html")

@jwt_cookie_required
def electricians_page(request):
    return render(request, "electricians.html")

@jwt_cookie_required
def jobs_page(request):
    return render(request, "jobs.html")

@jwt_cookie_required
def tasks_page(request):
    return render(request, "tasks.html")

@jwt_cookie_required
def materials_page(request):
    return render(request, "materials.html")

@jwt_cookie_required
def profile_page(request):
    return render(request, "profile.html")

@jwt_cookie_required
def reports_page(request):
    return render(request, "reports.html")


# -------------------- AUTH (HTML FLOW) --------------------

def register_view(request):
    if request.COOKIES.get('access_token'):
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name') 
        email = request.POST.get('email')
        # phone = request.POST.get('phone') # Grab the phone
        # role = request.POST.get('role')   # Grab the role
        password = request.POST.get('password')

        # Basic Validation
        # if not role or role == "Select Role":
        #     return render(request, 'register.html', {'error': 'Please select a valid role.'})

        if User.objects.filter(username=name).exists():
            return render(request, 'register.html', {'error': 'That name is already taken.'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'That email is already registered.'})

        # Create the user securely
        user = User.objects.create_user(username=name, email=email, password=password)

        # NOTE: If you created a UserProfile model for Phone/Role, you would save it here:
        # UserProfile.objects.create(user=user, phone=phone, role=role)

        refresh = RefreshToken.for_user(user)
        response = redirect('dashboard')
        response.set_cookie(
            key='access_token', 
            value=str(refresh.access_token), 
            httponly=True,
            samesite='Lax'
        )
        return response

    return render(request, 'register.html')

def login_view(request):
    if request.COOKIES.get('access_token'):
        return redirect('dashboard')

    if request.method == 'POST':
        username_input = request.POST.get('username')
        password_input = request.POST.get('password')

        print(f"Attempting login with username: {username_input} and password: {password_input}")  # Debugging line
        # user = User.objects.create_user("admin", "pk@gmail.com", "1234")
        user = authenticate(request, username=username_input, password=password_input)
        
        if user is not None:
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            response = redirect('dashboard') 
            response.set_cookie(
                key='access_token', 
                value=access_token, 
                httponly=True, 
                secure=False,  
                samesite='Lax'
            )
            return response
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password.'})
            
    return render(request, 'login.html')


# ---------------- LOGOUT ----------------

def logout_view(request):
    response = redirect('login') 
    response.delete_cookie('access_token')
    return response


# -------------------- API (JSON for fetch/Postman) --------------------
# ... (Keep your API views exactly as they were) ...

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