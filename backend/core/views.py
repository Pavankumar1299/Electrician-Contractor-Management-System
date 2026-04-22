from django.shortcuts import get_object_or_404, redirect, render
from .models import Electrician, Job, Task, Material, UserProfile, Notification
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.contrib.auth.decorators import login_required
from functools import wraps
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from django.utils import timezone
from datetime import timedelta

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

        messages.success(request, "Account created successfully")
        request.session.save()  # Ensure session is saved before setting cookie
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
            # ensure profile exists
            UserProfile.objects.get_or_create(user=user)

            refresh = RefreshToken.for_user(user)

            messages.success(request, "Logged in successfully")

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

    # ROLE BASED DATA
    if role == 'ELECTRICIAN':
        tasks = Task.objects.filter(electrician__user=request.user)
        jobs = Job.objects.filter(electrician__user=request.user)
    else:
        tasks = Task.objects.all()
        jobs = Job.objects.all()

    electricians_count = Electrician.objects.count()
    contractors_count = UserProfile.objects.filter(role='CONTRACTOR').count()

    pending_tasks = tasks.filter(status='Pending').count()
    in_progress_tasks = tasks.filter(status='In Progress').count()
    completed_tasks = tasks.filter(status='Completed').count()

    total_tasks = tasks.count()
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    recent_tasks = tasks.order_by('-updated_at')[:5]

    
    # DEADLINE ALERTS (only for electrician)
    deadline_notifications = []

    if role == 'ELECTRICIAN':
        upcoming_tasks = tasks.filter(
            deadline__isnull=False,
            status__in=['Pending', 'In Progress']
        )

        for task in upcoming_tasks:
            time_left = task.deadline - timezone.now()

            if timedelta(0) < time_left <= timedelta(hours=24):
                deadline_notifications.append({
                    'message': f"⚠️ Deadline approaching: {task.title}",
                    'time': "Due soon"
                })
        # new line end

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    context = {
        'electricians_count': electricians_count,
        'contractors_count': contractors_count,
        'jobs_count': jobs.count(),
        'tasks_count': total_tasks,

        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,

        'completion_rate': round(completion_rate, 2),
        'notifications': notifications,
        'deadline_notifications': deadline_notifications,

        'role': role,
        'unread_count': unread_count,
        'recent_tasks': recent_tasks,
    }

    return render(request, 'dashboard.html', context)


# ------  NOTIFICATION  -------------
@jwt_cookie_required
def notifications_page(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'notifications.html', {
        'notifications': notifications
    })

@jwt_cookie_required
def mark_notification_read(request, id):
    notification = get_object_or_404(Notification, id=id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications')

@jwt_cookie_required
def delete_notification(request, id):
    notification = get_object_or_404(Notification, id=id, user=request.user)
    notification.delete()
    return redirect('notifications')


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

        messages.success(request, "Electrician added successfully")
        return redirect('electricians')

    return render(request, 'add_electrician.html')

@jwt_cookie_required
@role_required(['ADMIN'])
def edit_electrician(request, id):
    electrician = get_object_or_404(Electrician, id=id)

    if request.method == 'POST':
        electrician.name = request.POST['name']
        electrician.phone = request.POST['phone']
        electrician.email = request.POST['email']
        electrician.experience = request.POST['experience']
        electrician.save()

        messages.info(request, "Electrician updated successfully")
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
        
        messages.error(request, "Electrician deleted successfully")
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
            electrician_id=electrician_id if electrician_id else None,

            # Just add this line to grab the image file!
            image=request.FILES.get('image')
        )

        messages.success(request, "Job added successfully")
        return redirect('jobs')

    return render(request, 'add_job.html', {
        'electricians': electricians
    })

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
def edit_job(request, id):
    job = get_object_or_404(Job, id=id)
    electricians = Electrician.objects.all()

    if request.method == 'POST':
        job.title = request.POST['title']
        job.description = request.POST['description']
        job.location = request.POST['location']
        job.deadline = request.POST['deadline']
        job.electrician_id = request.POST.get('electrician') or None

        # Grab the new image if one was uploaded
        new_image = request.FILES.get('image')
        if new_image:
            job.image = new_image

        job.save()

        messages.info(request, "Job updated successfully")
        return redirect('jobs')
    
    return render(request, 'edit_job.html', {
        'job': job,
        'electricians': electricians
    })

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
def delete_job(request, id):
    job = get_object_or_404(Job, id=id)

    if request.method == 'POST':
        job.delete()
        
        messages.error(request, "Job deleted successfully")
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

        deadline = request.POST.get('deadline')

        if deadline:
            dt = parse_datetime(deadline)
            deadline = make_aware(dt)

        task = Task.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            job_id=request.POST['job'],
            electrician_id=request.POST.get('electrician') or None,
            status=request.POST['status'],
            deadline=deadline 
        )

        if task.electrician and task.electrician.user:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"New task assigned: {task.title}"
            )

        # print("Notification created for electrician")
        messages.success(request, "Task added successfully")

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

        # STORE OLD VALUES FIRST
        old_status = task.status
        new_status = request.POST.get('status')
        old_electrician = task.electrician_id

        # UPDATE FIELDS
        task.title = request.POST['title']
        task.description = request.POST['description']
        task.job_id = request.POST['job']
        task.electrician_id = request.POST.get('electrician') or None

        # SAFE DEADLINE
        deadline = request.POST.get('deadline')
        if deadline:
            dt = parse_datetime(deadline)
            task.deadline = make_aware(dt)

        task.status = new_status

        # Grab the file if it was uploaded
        report = request.FILES.get('report_file')
        if report:
            task.report_file = report

        # SAVE FIRST
        task.save()

        

        # ============ NOTIFICATIONS= ============

        # 1. TASK COMPLETED → ADMIN
        if new_status == "Completed" and old_status != "Completed":
            admin_users = User.objects.filter(userprofile__role='ADMIN')

            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"Task completed: {task.title} by {task.electrician.name}"
                )
            print("Admin notified")
            print("OLD:", old_status)
            print("NEW:", request.POST.get('status'))

        # 2. TASK UPDATED → ELECTRICIAN
        # CASE 1: First time assignment (no old electrician)
        if old_electrician is None and task.electrician:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"New task assigned: {task.title}"
            )
            # print("First assignment")

        # CASE 2: Electrician changed
        elif old_electrician != task.electrician_id and task.electrician:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"New task assigned: {task.title}"
            )
            # print("Reassigned")

        # CASE 3: Only update (same electrician)
        elif task.electrician and task.electrician.user:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"Task updated: {task.title}"
            )
            # print("Updated only")

        messages.info(request, "Task updated successfully")
        return redirect('tasks')


    return render(request, 'edit_task.html', {
        'task': task,
        'jobs': jobs,
        'electricians': electricians
    })

@jwt_cookie_required
def delete_task(request, id):
    task = get_object_or_404(Task, id=id)

    if request.method == 'POST':
        task.delete()
        
        messages.error(request, "Task deleted successfully")
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
        
        messages.success(request, "Material added successfully")
        return redirect('materials')
    

    return render(request, 'add_material.html', {'jobs': jobs})

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
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

        messages.info(request, "Material updated successfully")
        return redirect('materials')

    

    return render(request, 'edit_material.html', {
        'material': material,
        'jobs': jobs
    })

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
def delete_material(request, id):
    material = get_object_or_404(Material, id=id)

    if request.method == 'POST':
        material.delete()

        messages.error(request, "Material deleted successfully")
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

@jwt_cookie_required
# @login_required
def update_profile(request):
    user = request.user
    profile = user.userprofile

    if request.method == 'POST':
        user.username = request.POST.get('username')
        profile.phone = request.POST.get('phone')
        user.email = request.POST.get('email')

        # NEW: Handle profile picture upload
        profile_pic = request.FILES.get('profile_picture')
        if profile_pic:
            profile.profile_picture = profile_pic

        user.save()
        profile.save()

        messages.success(request, "Profile updated successfully")
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
