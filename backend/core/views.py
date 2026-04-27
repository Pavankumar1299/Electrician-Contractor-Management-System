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
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import F
import random



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


# -------------------- CONTRACTORS --------------------
@jwt_cookie_required
@role_required(['ADMIN'])
def contractors_view(request):
    # Fetch all Users who have a UserProfile with the role 'CONTRACTOR'
    query = request.GET.get('name')
    contractors = User.objects.filter(userprofile__role='CONTRACTOR')
    
    if query:
        contractors = contractors.filter(first_name__icontains=query)

    return render(request, 'contractors.html', {'contractors': contractors})

@jwt_cookie_required
@role_required(['ADMIN'])
def add_contractor(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST['phone']

        # 1. Create a safe, unique username for the built-in User model
        safe_username = f"{name.replace(' ', '').lower()}_{random.randint(1000, 9999)}"
        
        # 2. Create the User (Password is defaulted since they are added by Admin)
        user = User.objects.create_user(username=safe_username, email=email, password='defaultpassword123')
        user.first_name = name
        user.save()

        # 3. Update the automatically created UserProfile
        profile = user.userprofile
        profile.role = 'CONTRACTOR'
        profile.phone = phone
        profile.save()

        messages.success(request, "Contractor added successfully")
        return redirect('contractors')

    return render(request, 'add_contractor.html')

@jwt_cookie_required
@role_required(['ADMIN'])
def edit_contractor(request, id):
    contractor_user = get_object_or_404(User, id=id, userprofile__role='CONTRACTOR')

    if request.method == 'POST':
        # Update User model fields
        contractor_user.first_name = request.POST['name']
        contractor_user.email = request.POST['email']
        contractor_user.save()

        # Update UserProfile model fields
        profile = contractor_user.userprofile
        profile.phone = request.POST['phone']
        profile.save()

        messages.info(request, "Contractor updated successfully")
        return redirect('contractors')

    return render(request, 'edit_contractor.html', {'contractor': contractor_user})

@jwt_cookie_required
@role_required(['ADMIN'])
def delete_contractor(request, id):
    contractor_user = get_object_or_404(User, id=id, userprofile__role='CONTRACTOR')

    if request.method == 'POST':
        # Deleting the User automatically deletes the UserProfile due to on_delete=models.CASCADE
        contractor_user.delete()
        
        messages.error(request, "Contractor deleted successfully")
        return redirect('contractors')

    return render(request, 'delete_contractor.html', {'contractor': contractor_user})


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
    job_filter = request.GET.get('job', '')

    # 1. DEFINE BASE QUERYSET (Based on Role Security)
    if role == 'ELECTRICIAN':
        # Electricians only see their own tasks
        tasks = Task.objects.filter(electrician__user=request.user).select_related('job')

        # Pro-Tip: Also limit the dropdown to only show jobs they are assigned to!
        # jobs = Job.objects.filter(electrician__user=request.user) 
        
        # Fetch all unique jobs that are linked to the user's assigned tasks!
        jobs = Job.objects.filter(tasks__electrician__user=request.user).distinct()
    else:
        # Admins and Contractors see everything
        tasks = Task.objects.select_related('job').all()
        jobs = Job.objects.all()

    # 2. APPLY JOB FILTER
    if job_filter:
        tasks = tasks.filter(job_id=job_filter)

    # 3. APPLY STATUS FILTER
    if status:
        tasks = tasks.filter(status=status)

    return render(request, 'tasks.html', {
        'tasks': tasks,
        'jobs': jobs,
    })

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

        # 1. TASK COMPLETED → ADMIN & JOB COMPLETION CHECK
        if new_status == "Completed" and old_status != "Completed":
            admin_users = User.objects.filter(userprofile__role='ADMIN')

            # Notify Admin that the specific task is done
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"Task completed: {task.title} by {task.electrician.name}"
                )

            # --- NEW: CHECK IF THE ENTIRE JOB IS NOW COMPLETE ---
            parent_job = task.job
            incomplete_tasks_exist = Task.objects.filter(job=parent_job).exclude(status='Completed').exists()
            
            if not incomplete_tasks_exist:
                # Notify Admins that the whole job is done
                for admin in admin_users:
                    Notification.objects.create(
                        user=admin,
                        message=f"🎉 JOB COMPLETE: All tasks for '{parent_job.title}' are finished!"
                    )
                
                # Notify the Lead Contractor (if they aren't also an admin)
                if parent_job.electrician and parent_job.electrician.user:
                    if parent_job.electrician.user not in admin_users:
                        Notification.objects.create(
                            user=parent_job.electrician.user,
                            message=f"🎉 JOB COMPLETE: Your site phase '{parent_job.title}' is fully finished!"
                        )

        # 2. TASK UPDATED/ASSIGNED → ELECTRICIAN
        # CASE 1: First time assignment (no old electrician)
        if old_electrician is None and task.electrician:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"New task assigned: {task.title}"
            )

        # CASE 2: Electrician changed / Reassigned
        elif old_electrician != task.electrician_id and task.electrician:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"New task assigned to you: {task.title}"
            )

        # CASE 3: Only update (same electrician, e.g., deadline or description changed)
        elif task.electrician and task.electrician.user:
            # We don't want to spam them if they just clicked "Completed" themselves
            if new_status != "Completed" or old_status == new_status:
                Notification.objects.create(
                    user=task.electrician.user,
                    message=f"Task updated: {task.title}"
                )

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
    jobs = Job.objects.all() # Fetch jobs for the dropdown filter

    # 1. Get filter parameters from the URL
    search_query = request.GET.get('q', '')
    job_filter = request.GET.get('job', '')
    stock_filter = request.GET.get('stock', '')

    # 2. Apply Text Search
    if search_query:
        materials = materials.filter(name__icontains=search_query)

    # 3. Apply Job Filter
    if job_filter:
        materials = materials.filter(job_id=job_filter)

    # 4. Apply Stock Status Filter
    if stock_filter == 'out_of_stock':
        # Remaining is 0 or less
        materials = materials.filter(quantity__lte=F('used_quantity'))
    elif stock_filter == 'low_stock':
        # Remaining is greater than 0 but less than or equal to 10
        materials = materials.annotate(
            remaining_stock=F('quantity') - F('used_quantity')
        ).filter(remaining_stock__gt=0, remaining_stock__lte=10)
    elif stock_filter == 'in_stock':
        # Remaining is strictly greater than 0
        materials = materials.filter(quantity__gt=F('used_quantity'))

    return render(request, 'materials.html', {
        'materials': materials,
        'jobs': jobs, # Pass jobs to the template for the dropdown
    })

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


# ----------- ADMIN - VIEW AS (IMPERSONATION) ------------
@jwt_cookie_required
@role_required(['ADMIN'])
def view_as_user(request, id):
    electrician = get_object_or_404(Electrician, id=id)
    target_user = electrician.user

    # Safety check: Ensure the electrician actually has a login account
    if not target_user:
        messages.error(request, f"{electrician.name} does not have a user account set up yet.")
        return redirect('electricians')

    # Save the original Admin's user ID in the session
    request.session['original_admin_id'] = request.user.id

    # Generate a new token for the electrician
    refresh = RefreshToken.for_user(target_user)

    messages.success(request, f"You are now viewing the system as {electrician.name}")
    
    response = redirect('dashboard')
    response.set_cookie(
        key='access_token',
        value=str(refresh.access_token),
        httponly=True,
        samesite='Lax'
    )
    return response

# -------------------- VIEW AS CONTRACTOR --------------------
@jwt_cookie_required
@role_required(['ADMIN'])
def view_as_contractor(request, id):
    contractor = get_object_or_404(User, id=id, userprofile__role='CONTRACTOR')

    # Save the original Admin's ID and remember we came from the Contractors page
    request.session['original_admin_id'] = request.user.id
    request.session['impersonation_return_url'] = 'contractors'

    # Generate a new token for the contractor
    refresh = RefreshToken.for_user(contractor)

    display_name = contractor.first_name if contractor.first_name else contractor.username
    messages.success(request, f"You are now viewing the system as {display_name}")
    
    response = redirect('dashboard')
    response.set_cookie(
        key='access_token',
        value=str(refresh.access_token),
        httponly=True,
        samesite='Lax'
    )
    return response

# -------------------- STOP VIEWING AS --------------------
@jwt_cookie_required
def stop_viewing_as(request):
    if 'original_admin_id' not in request.session:
        return redirect('dashboard')

    original_admin_id = request.session['original_admin_id']
    admin_user = get_object_or_404(User, id=original_admin_id)

    # Determine which page to return the Admin to (default to dashboard if unknown)
    return_url = request.session.get('impersonation_return_url', 'dashboard')

    # Clear the session variables
    del request.session['original_admin_id']
    if 'impersonation_return_url' in request.session:
        del request.session['impersonation_return_url']

    # Generate a fresh token for the Admin
    refresh = RefreshToken.for_user(admin_user)

    messages.info(request, "Welcome back. Restored Admin session.")
    
    response = redirect(return_url)
    response.set_cookie(
        key='access_token',
        value=str(refresh.access_token),
        httponly=True,
        samesite='Lax'
    )
    return response


