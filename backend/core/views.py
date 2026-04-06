from django.shortcuts import get_object_or_404, redirect, render
from django.shortcuts import render, redirect
from .models import Electrician, Job, Task, Material # Removed User from here to use default auth User
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
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
def electricians_page(request):
    return render(request, "electricians.html")

@jwt_cookie_required
def jobs_page(request):
    jobs = Job.objects.select_related('electrician').all()
    return render(request, 'jobs.html', {'jobs': jobs})

@jwt_cookie_required
def tasks_page(request):
    tasks = Task.objects.select_related('job', 'electrician').all()
    return render(request, 'tasks.html', {'tasks': tasks})

@jwt_cookie_required
def materials_page(request):
    materials = Material.objects.select_related('job').all()
    return render(request, 'materials.html', {'materials': materials})

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

@jwt_cookie_required
def dashboard_view(request):
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='Completed').count()

    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0


    context = {
        'electricians_count': Electrician.objects.count(),
        'jobs_count': Job.objects.count(),
        'tasks_count': Task.objects.count(),

        'pending_tasks': Task.objects.filter(status='Pending').count(),
        'in_progress_tasks': Task.objects.filter(status='In Progress').count(),
        'completed_tasks': Task.objects.filter(status='Completed').count(),

        'completion_rate': round(completion_rate, 2)
    }
    return render(request, 'dashboard.html', context)

def electricians_view(request):
    electricians = Electrician.objects.all()
    print(electricians)
    return render(request, 'electricians.html', {
        'electricians': electricians
    })

def add_electrician(request):
    if request.method == 'POST':
        Electrician.objects.create(
            name=request.POST['name'],
            phone=request.POST['phone'],
            email=request.POST['email'],
            experience=request.POST['experience']
        )
        return redirect('electricians')

    return render(request, 'add_electrician.html')

def edit_electrician(request, id):
    electrician = get_object_or_404(Electrician, id=id)

    if request.method == 'POST':
        electrician.name = request.POST['name']
        electrician.phone = request.POST['phone']
        electrician.email = request.POST['email']
        electrician.experience = request.POST['experience']
        electrician.save()

        return redirect('electricians')

    return render(request, 'edit_electrician.html', {
        'electrician': electrician
    })

def delete_electrician(request, id):
    electrician = get_object_or_404(Electrician, id=id)

    if request.method == 'POST':
        electrician.delete()
        return redirect('electricians')

    return render(request, 'delete_electrician.html', {
        'electrician': electrician
    })

def add_job(request):
    electricians = Electrician.objects.all()

    if request.method == 'POST':
        electrician_id = request.POST.get('electrician')

        Job.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            location=request.POST['location'],
            deadline=request.POST['deadline'],
            electrician_id=electrician_id if electrician_id else None
        )

        return redirect('jobs')

    return render(request, 'add_job.html', {
        'electricians': electricians
    })

def edit_job(request, id):
    job = get_object_or_404(Job, id=id)
    electricians = Electrician.objects.all()

    if request.method == 'POST':
        job.title = request.POST['title']
        job.description = request.POST['description']
        job.location = request.POST['location']
        job.deadline = request.POST['deadline']
        job.electrician_id = request.POST.get('electrician') or None
        job.save()

        return redirect('jobs')

    return render(request, 'edit_job.html', {
        'job': job,
        'electricians': electricians
    })

def delete_job(request, id):
    job = get_object_or_404(Job, id=id)

    if request.method == 'POST':
        job.delete()
        return redirect('jobs')

    return render(request, 'delete_job.html', {'job': job})

def add_task(request):
    jobs = Job.objects.all()
    electricians = Electrician.objects.all()

    if request.method == 'POST':
        Task.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            job_id=request.POST['job'],
            electrician_id=request.POST.get('electrician') or None,
            status=request.POST['status']
        )
        return redirect('tasks')

    return render(request, 'add_task.html', {
        'jobs': jobs,
        'electricians': electricians
    })

def edit_task(request, id):
    task = get_object_or_404(Task, id=id)
    jobs = Job.objects.all()
    electricians = Electrician.objects.all()

    if request.method == 'POST':
        task.title = request.POST['title']
        task.description = request.POST['description']
        task.job_id = request.POST['job']
        task.electrician_id = request.POST.get('electrician') or None
        task.status = request.POST['status']
        task.save()

        return redirect('tasks')

    return render(request, 'edit_task.html', {
        'task': task,
        'jobs': jobs,
        'electricians': electricians
    })

def delete_task(request, id):
    task = get_object_or_404(Task, id=id)

    if request.method == 'POST':
        task.delete()
        return redirect('tasks')

    return render(request, 'delete_task.html', {'task': task})

def add_material(request):
    jobs = Job.objects.all()

    if request.method == 'POST':
        Material.objects.create(
            name=request.POST['name'],
            quantity=request.POST['quantity'],
            used_quantity=request.POST.get('used_quantity') or 0,
            unit=request.POST['unit'],
            job_id=request.POST['job']
        )
        return redirect('materials')

    return render(request, 'add_material.html', {'jobs': jobs})

def edit_material(request, id):
    material = get_object_or_404(Material, id=id)
    jobs = Job.objects.all()

    if request.method == 'POST':
        material.name = request.POST['name']
        material.quantity = request.POST['quantity']
        material.unit = request.POST['unit']
        material.used_quantity = request.POST['used_quantity']
        material.job_id = request.POST['job']
        material.save()

        return redirect('materials')

    return render(request, 'edit_material.html', {
        'material': material,
        'jobs': jobs
    })

def delete_material(request, id):
    material = get_object_or_404(Material, id=id)

    if request.method == 'POST':
        material.delete()
        return redirect('materials')

    return render(request, 'delete_material.html', {'material': material})

