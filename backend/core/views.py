from django.shortcuts import get_object_or_404, redirect, render
from .models import Electrician, Job, Task, Material, UserProfile
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.contrib.auth.decorators import login_required
from functools import wraps
from .models import Notification

# -------------------- SECURITY DECORATOR --------------------
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
            UserProfile.objects.get_or_create(user=request.user)

        except (InvalidToken, AuthenticationFailed):
            # Token is expired or tampered with
            response = redirect('login')
            response.delete_cookie('access_token')
            return response
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            role = request.user.userprofile.role

            if role not in allowed_roles:
                return redirect('dashboard')  # or show error

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# -------------------- LOGIN & SIGNUP --------------------
def register_view(request):
    if request.COOKIES.get('access_token'):
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if not role:
            return render(request, 'register.html', {'error': 'Please select a role'})

        if User.objects.filter(username=name).exists():
            return render(request, 'register.html', {'error': 'Username taken'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email already registered'})

        user = User.objects.create_user(
            username=name,
            email=email,
            password=password
        )

        if role == "ELECTRICIAN":
            Electrician.objects.create(
                user=user,
                name=name,
                email=email,
                phone=phone,
                experience=0
            )

        # assign role here
        profile = user.userprofile
        profile.role = role
        profile.phone = phone
        profile.save()

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

        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            # 🔥 ensure profile exists
            UserProfile.objects.get_or_create(user=user)

            refresh = RefreshToken.for_user(user)

            response = redirect('dashboard')
            response.set_cookie(
                key='access_token',
                value=str(refresh.access_token),
                httponly=True,
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


# -------------------- PAGE VIEWS --------------------
# --------------------- HOME --------------------
def home_page(request):
    return render(request, "index.html")


# -------------------- DASHBOARD --------------------
@jwt_cookie_required
def dashboard_view(request):

    role = request.user.userprofile.role

    if role == 'ELECTRICIAN':
        tasks = Task.objects.filter(electrician__user=request.user)
    else:
        tasks = Task.objects.all()

    electricians_count = UserProfile.objects.filter(role='ELECTRICIAN').count()
    contractors_count = UserProfile.objects.filter(role='CONTRACTOR').count()

    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='Completed').count()

    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    context = {
        'electricians_count': electricians_count,
        'contractors_count': contractors_count,
        'jobs_count': Job.objects.count(),
        'tasks_count': Task.objects.count(),

        'pending_tasks': Task.objects.filter(status='Pending').count(),
        'in_progress_tasks': Task.objects.filter(status='In Progress').count(),
        'completed_tasks': Task.objects.filter(status='Completed').count(),

        'completion_rate': round(completion_rate, 2),
        
        'notifications': notifications
    }
    return render(request, 'dashboard.html', context)


# -------------------- ELECTRICIANS --------------------
@jwt_cookie_required
@login_required
def electricians_view(request):
    name = request.GET.get('name')

    if name:
        electricians = Electrician.objects.filter(name__icontains=name)
    else:
        electricians = Electrician.objects.all()

    return render(request, 'electricians.html', {
        'electricians': electricians
    })

@jwt_cookie_required
@role_required(['ADMIN'])
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

@jwt_cookie_required
@role_required(['ADMIN'])
def delete_electrician(request, id):
    electrician = get_object_or_404(Electrician, id=id)

    if request.method == 'POST':
        electrician.delete()
        return redirect('electricians')

    return render(request, 'delete_electrician.html', {
        'electrician': electrician
    })


# -------------------- JOBS --------------------
@jwt_cookie_required
def jobs_page(request):
    query = request.GET.get('q')

    if query:
        jobs = Job.objects.filter(title__icontains=query)
    else:
        jobs = Job.objects.all()

    # jobs = Job.objects.select_related('electrician').all()
    return render(request, 'jobs.html', {'jobs': jobs})

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
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


# -------------------- TASKS --------------------
@jwt_cookie_required
def tasks_page(request):
    role = request.user.userprofile.role
    status = request.GET.get('status')

    if role == 'ELECTRICIAN':
        tasks = Task.objects.filter(electrician__user=request.user)
    else:
        tasks = Task.objects.all()

    if status:
        tasks = tasks.filter(status=status)

    return render(request, 'tasks.html', {'tasks': tasks})

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
def add_task(request):
    jobs = Job.objects.all()
    electricians = Electrician.objects.all()

    if request.method == 'POST':
        task = Task.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            job_id=request.POST['job'],
            electrician_id=request.POST.get('electrician') or None,
            status=request.POST['status']
        )

        if task.electrician and task.electrician.user:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"New task assigned: {task.title}"
            )
        return redirect('tasks')

    return render(request, 'add_task.html', {
        'jobs': jobs,
        'electricians': electricians
    })

@jwt_cookie_required
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


# -------------------- MATERIALS --------------------
@jwt_cookie_required
def materials_page(request):
    materials = Material.objects.select_related('job').all()
    return render(request, 'materials.html', {'materials': materials})

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
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


# -------------------- PROFILE --------------------
@jwt_cookie_required
@login_required
def profile_page(request):
    user = request.user
    profile = user.userprofile

    return render(request, 'profile.html', {
        'user': user,
        'role': profile.role
    })

# @login_required
@jwt_cookie_required
def update_profile(request):
    user = request.user
    profile = user.userprofile

    if request.method == 'POST':
        user.username = request.POST.get('username')
        profile.phone = request.POST.get('phone')
        user.email = request.POST.get('email')

        user.save()
        profile.save()

        return redirect('profile')

    return render(request, 'update_profile.html', {
        'user': user,
        'profile': profile
    })


# -------------------- REPORTS --------------------
@jwt_cookie_required
@role_required(['ADMIN'])
def reports_page(request):
    from django.utils.timezone import now
    from django.db.models import Count

    today = now().date()

    tasks_today = Task.objects.filter(created_at__date=today)
    completed_tasks = Task.objects.filter(status='Completed')

    activity = Task.objects.values('electrician__name').annotate(count=Count('id'))

    context = {
        'electricians': Electrician.objects.count(),
        'jobs': Job.objects.count(),
        'tasks': Task.objects.count(),
        'materials': Material.objects.count(),

        'pending': Task.objects.filter(status='Pending').count(),
        'in_progress': Task.objects.filter(status='In Progress').count(),
        'completed': Task.objects.filter(status='Completed').count(),

        'tasks_today': tasks_today,
        'completed_tasks': completed_tasks,
        'activity': activity,
    }

    return render(request, 'reports.html', context)
