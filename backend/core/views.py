from django.shortcuts import get_object_or_404, redirect, render
from .models import Electrician, Job, Task, Material, UserProfile, Notification, TaskPayment
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
import re
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q





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
        confirm_password = request.POST.get('confirm_password') # NEW: Grab confirm password
        role = request.POST.get('role')

        # ==========================================
        # 1. ROLE & USERNAME VALIDATION
        # ==========================================
        if not role:
            messages.error(request, "Please select a role.")
            return redirect('register')

        if len(name) < 4:
            messages.error(request, "Username must be at least 4 characters long.")
            return redirect('register')

        if User.objects.filter(username=name).exists():
            messages.error(request, "Username is already taken. Please choose another.")
            return redirect('register')
        
        # ==========================================
        # 2. EMAIL VALIDATION
        # ==========================================
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Please enter a valid email address.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return redirect('register')

        # ==========================================
        # 3. PHONE NUMBER VALIDATION
        # ==========================================
        if not re.match(r'^\d{10}$', phone):
            messages.error(request, "Invalid phone number. It must be exactly 10 digits.")
            return redirect('register')
            
        if UserProfile.objects.filter(phone=phone).exists():
            messages.error(request, "This phone number is already registered to another account.")
            return redirect('register')

        # ==========================================
        # 4. PASSWORD VALIDATION
        # ==========================================
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        # Require at least 8 characters, 1 letter, and 1 number
        if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            messages.error(request, "Password must be at least 8 characters long and contain at least one letter and one number.")
            return redirect('register')

        # ==========================================
        # ALL CHECKS PASSED -> CREATE THE ACCOUNT
        # ==========================================
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

        # Assign role and phone to the profile
        profile = user.userprofile
        profile.role = role
        profile.phone = phone
        profile.save()

        refresh = RefreshToken.for_user(user)

        messages.success(request, "Account created successfully!")
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


# -------------------- CHANGE PASSWORD --------------------
@jwt_cookie_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        user = request.user

        # 1. VERIFY OLD PASSWORD
        if not user.check_password(old_password):
            messages.error(request, "Incorrect current password.")
            return redirect('change_password')

        # 2. MATCH CHECK
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('change_password')

        # 3. PREVENT REUSING OLD PASSWORD
        if old_password == new_password:
            messages.error(request, "New password cannot be the same as the old password.")
            return redirect('change_password')

        # 4. REGEX STRENGTH VALIDATION (Matches your signup rules!)
        if len(new_password) < 8 or not re.search(r'[A-Za-z]', new_password) or not re.search(r'\d', new_password):
            messages.error(request, "Password must be at least 8 characters long and contain at least one letter and one number.")
            return redirect('change_password')

        # ==========================================
        # 5. ALL CHECKS PASSED -> UPDATE PASSWORD
        # ==========================================
        user.set_password(new_password)
        user.save()

        # 6. RE-ISSUE JWT COOKIE SO THEY DON'T GET LOGGED OUT
        refresh = RefreshToken.for_user(user)
        
        messages.success(request, "Your password has been updated securely.")
        
        # Redirect back to profile, but attach the new cookie
        response = redirect('profile') 
        response.set_cookie(
            key='access_token',
            value=str(refresh.access_token),
            httponly=True,
            samesite='Lax'
        )
        return response

    return render(request, 'change_password.html')


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

    # ==========================================
    # 1. SECURE DATA FENCING BY ROLE
    # ==========================================
    if role == 'ELECTRICIAN':
        tasks = Task.objects.filter(electrician__user=request.user)
        jobs = Job.objects.filter(tasks__electrician__user=request.user).distinct()
        electricians_count = 0  # Not relevant for Electrician dashboard
        contractors_count = 0

    elif role == 'CONTRACTOR':
        # --- NEW: Fenced Data for Contractors ---
        jobs = Job.objects.filter(assigned_contractor=request.user)
        tasks = Task.objects.filter(job__assigned_contractor=request.user)
        
        # Only count electricians who have tasks under this specific Contractor's jobs
        electricians_count = Electrician.objects.filter(
            tasks__job__assigned_contractor=request.user
        ).distinct().count()
        
        contractors_count = 0 # Not relevant for Contractor dashboard

    else:
        # ADMIN sees absolutely everything
        tasks = Task.objects.all()
        jobs = Job.objects.all()
        electricians_count = Electrician.objects.count()
        contractors_count = UserProfile.objects.filter(role='CONTRACTOR').count()

    # ==========================================
    # 2. DYNAMIC METRICS (Based on fenced data)
    # ==========================================
    pending_tasks = tasks.filter(status='Pending').count()
    in_progress_tasks = tasks.filter(status='In Progress').count()
    completed_tasks = tasks.filter(status='Completed').count()

    total_tasks = tasks.count()
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Recent tasks overview will now securely show only the contractor's tasks
    recent_tasks = tasks.order_by('-updated_at')[:5]

    # ==========================================
    # 3. NOTIFICATIONS LOGIC
    # ==========================================
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Fulfilling your requirement: Admin only sees 'Completed' notifications
    if role == 'ADMIN':
        notifications = notifications.filter(message__icontains='Completed')

    unread_count = notifications.filter(is_read=False).count()

    # ==========================================
    # 4. FINANCIALS & ALERTS (Electrician Only)
    # ==========================================
    total_earned = 0
    deadline_notifications = []

    if role == 'ELECTRICIAN':
        # Financials
        my_payments = TaskPayment.objects.filter(electrician=request.user).select_related('task')
        total_earned = sum(p.amount for p in my_payments if p.status == 'PAID' and p.amount)

        # Deadline Alerts
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

    # ==========================================
    # 5. CONTEXT RENDERING
    # ==========================================
    context = {
        'electricians_count': electricians_count,
        'contractors_count': contractors_count,
        'jobs_count': jobs.count(),
        'tasks_count': total_tasks,

        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,

        'completion_rate': round(completion_rate, 2),
        'notifications': notifications[:10], # Limit to 10 so the UI doesn't break
        'deadline_notifications': deadline_notifications,

        'role': role,
        'unread_count': unread_count,
        'recent_tasks': recent_tasks,

        'total_earned': total_earned
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

        # 1. VALIDATION
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Invalid email format.")
            return redirect('add_contractor')
            
        if not re.match(r'^\d{10}$', phone):
            messages.error(request, "Phone number must be exactly 10 digits.")
            return redirect('add_contractor')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('add_contractor')

        # 2. CREATE ACCOUNT
        safe_username = f"{name.replace(' ', '').lower()}_{random.randint(1000, 9999)}"
        default_password = 'ecms@123'
        
        user = User.objects.create_user(username=safe_username, email=email, password=default_password)
        user.first_name = name
        user.save()

        profile = user.userprofile
        profile.role = 'CONTRACTOR'
        profile.phone = phone
        profile.save()

        # 3. SEND ONBOARDING EMAIL
        subject = 'Welcome to ECMS - Your Contractor Account'
        message = f"Hello {name},\n\nAn Admin has created a Contractor account for you on the ECMS platform.\n\nHere are your login credentials:\nUsername: {safe_username}\nPassword: {default_password}\n\nPlease log in and change your password immediately.\n\nBest,\nECMS Admin Team"
        
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            messages.success(request, f"Contractor added! Login details emailed to {email}.")
        except Exception as e:
            # If the email fails (e.g., no internet), we don't want the app to crash
            messages.warning(request, "Contractor added, but the email failed to send. Please share credentials manually.")

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
# @jwt_cookie_required
# @login_required
# def electricians_view(request):
    name = request.GET.get('name')

    if name:
        electricians = Electrician.objects.filter(name__icontains=name)
    else:
        electricians = Electrician.objects.all()

    return render(request, 'electricians.html', {
        'electricians': electricians
    })


# --------------------- ELECTRICIANS --------------------
@jwt_cookie_required
@login_required
def electricians_view(request):
    role = request.user.userprofile.role
    name = request.GET.get('name')

    # ==========================================
    # 1. SECURE DATA FENCING BY ROLE
    # ==========================================
    if role == 'CONTRACTOR':
        # Contractor ONLY sees electricians assigned to their specific jobs
        # Note the use of 'tasks__...' and distinct() so an electrician isn't listed twice
        base_query = Electrician.objects.filter(
            tasks__job__assigned_contractor=request.user
        ).distinct()
    else:
        # Admins see the entire workforce
        base_query = Electrician.objects.all()

    # ==========================================
    # 2. APPLY SEARCH FILTER
    # ==========================================
    if name:
        electricians = base_query.filter(name__icontains=name)
    else:
        electricians = base_query

    return render(request, 'electricians.html', {
        'electricians': electricians
    })

@jwt_cookie_required
@role_required(['ADMIN'])
def add_electrician(request):
    if request.method == 'POST':
        name = request.POST['name']
        phone = request.POST['phone']
        email = request.POST['email']
        experience = request.POST.get('experience', 0)

        # 1. VALIDATION
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            messages.error(request, "Invalid email format.")
            return redirect('add_electrician')
            
        if not re.match(r'^\d{10}$', phone):
            messages.error(request, "Phone number must be exactly 10 digits.")
            return redirect('add_electrician')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('add_electrician')

        # 2. CREATE USER LOGIN ACCOUNT (Crucial Fix!)
        safe_username = f"{name.replace(' ', '').lower()}_{random.randint(1000, 9999)}"
        default_password = 'ecms@123'
        
        user = User.objects.create_user(username=safe_username, email=email, password=default_password)
        user.first_name = name
        user.save()

        profile = user.userprofile
        profile.role = 'ELECTRICIAN'
        profile.phone = phone
        profile.save()

        # 3. CREATE ELECTRICIAN RECORD
        Electrician.objects.create(
            user=user, # Link it to the login account
            name=name,
            phone=phone,
            email=email,
            experience=experience
        )

        # 4. SEND ONBOARDING EMAIL
        subject = 'Welcome to ECMS - Your Electrician Account'
        message = f"Hello {name},\n\nAn Admin has created an Electrician profile for you on the ECMS platform.\n\nHere are your login credentials:\nUsername: {safe_username}\nPassword: {default_password}\n\nPlease log in and change your password immediately.\n\nBest,\nECMS Admin Team"
        
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            messages.success(request, f"Electrician added! Login details emailed to {email}.")
        except Exception as e:
            messages.warning(request, "Electrician added, but the email failed to send. Please share credentials manually.")

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
    role = request.user.userprofile.role
    query = request.GET.get('q')

    # 1. Base Query with smart counting
    # This annotates each job with total_tasks and completed_tasks
    base_query = Job.objects.annotate(
        total_tasks=Count('tasks'),
        completed_tasks=Count('tasks', filter=Q(tasks__status='Completed'))
    )

    if role == 'CONTRACTOR':
        jobs = base_query.filter(assigned_contractor=request.user)
    else:
        jobs = base_query.all()

    if query:
        jobs = jobs.filter(title__icontains=query)

    # 2. Calculate the percentage for each job
    for job in jobs:
        if job.total_tasks > 0:
            job.progress_pct = int((job.completed_tasks / job.total_tasks) * 100)
        else:
            job.progress_pct = 0

    return render(request, 'jobs.html', {'jobs': jobs})

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
def add_job(request):
    # Fetch all users whose profile role is 'CONTRACTOR'
    contractors = User.objects.filter(userprofile__role='CONTRACTOR')

    if request.method == 'POST':
        # Grab the contractor ID from the form
        contractor_id = request.POST.get('contractor')

        Job.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            location=request.POST['location'],
            deadline=request.POST['deadline'],
            
            # --- NEW: Assign to Contractor instead of Electrician ---
            assigned_contractor_id=contractor_id if contractor_id else None,

            image=request.FILES.get('image')
        )

        # ... your existing Job.objects.create code ...
        job = Job.objects.last() # Get the job we just created

        # --- NEW: Notify the Contractor ---
        if job.assigned_contractor:
            from .models import Notification # ensure Notification is imported
            Notification.objects.create(
                user=job.assigned_contractor,
                message=f"New Job Assigned: {job.title} at {job.location}"
            )

        messages.success(request, "Job added successfully")
        return redirect('jobs')

    return render(request, 'add_job.html', {
        'contractors': contractors # Pass contractors to the template
    })

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
def edit_job(request, id):
    job = get_object_or_404(Job, id=id)
    
    # --- NEW: Fetch Contractors instead of Electricians ---
    from django.contrib.auth.models import User
    contractors = User.objects.filter(userprofile__role='CONTRACTOR')

    if request.method == 'POST':
        # Catch the new contractor input
        contractor_id = request.POST.get('contractor')

        job.title = request.POST['title']
        job.description = request.POST['description']
        job.location = request.POST['location']
        job.deadline = request.POST['deadline']
        
        # --- NEW: Save to the correct database field ---
        job.assigned_contractor_id = contractor_id if contractor_id else None

        if request.FILES.get('image'):
            job.image = request.FILES.get('image')

        job.save()

        messages.success(request, "Job updated successfully")
        return redirect('jobs')

    return render(request, 'edit_job.html', {
        'job': job,
        'contractors': contractors # Pass contractors to the template
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
        jobs = Job.objects.filter(tasks__electrician__user=request.user).distinct()
        
    elif role == 'CONTRACTOR':
        # --- NEW: Contractors only see tasks belonging to their assigned jobs ---
        tasks = Task.objects.filter(job__assigned_contractor=request.user).select_related('job')
        # The dropdown should also only show their jobs
        jobs = Job.objects.filter(assigned_contractor=request.user)
        
    else:
        # Admins see everything
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
        # Fetch the selected Job instance
        job_id = request.POST['job']
        job_instance = get_object_or_404(Job, id=job_id)
        
        deadline = request.POST.get('deadline')

        if deadline:
            dt = parse_datetime(deadline)
            deadline_aware = make_aware(dt)
            
            # --- NEW: Check if Task Deadline exceeds Job Deadline ---
            if deadline_aware.date() > job_instance.deadline:
                messages.error(request, f"Error: Task deadline cannot exceed the main Job deadline ({job_instance.deadline.strftime('%d-%b-%Y')}).")
                return redirect('add_task')
        else:
            deadline_aware = None

        task = Task.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            job_id=job_id,
            electrician_id=request.POST.get('electrician') or None,
            status=request.POST['status'],
            deadline=deadline_aware 
        )

        # --- NEW: Notify the Electrician ---
        if task.electrician and task.electrician.user:
            from .models import Notification
            Notification.objects.create(
                user=task.electrician.user,
                message=f"New Task Assigned: {task.title}"
            )

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

        # Fetch the selected Job instance
        job_id = request.POST['job']
        job_instance = get_object_or_404(Job, id=job_id)

        # SAFE DEADLINE & VALIDATION
        deadline = request.POST.get('deadline')
        if deadline:
            dt = parse_datetime(deadline)
            aware_deadline = make_aware(dt)
            
            # --- NEW: Check if Task Deadline exceeds Job Deadline ---
            if aware_deadline.date() > job_instance.deadline:
                messages.error(request, f"Error: Task deadline cannot exceed the main Job deadline ({job_instance.deadline.strftime('%d-%b-%Y')}).")
                return redirect('edit_task', id=task.id)
            
            task.deadline = aware_deadline

        # UPDATE FIELDS
        task.title = request.POST['title']
        task.description = request.POST['description']
        task.job_id = job_id
        task.electrician_id = request.POST.get('electrician') or None
        task.status = new_status

        # Grab the file if it was uploaded
        report = request.FILES.get('report_file')
        if report:
            task.report_file = report

        # SAVE FIRST
        task.save()

        # ============ NOTIFICATIONS ============
        # SAVE FIRST
        task.save()

        # ==========================================
        # NOTIFICATIONS LOGIC
        # ==========================================
        from .models import Notification
        from django.contrib.auth.models import User

        # 1. Did the Status Change? (Electrician -> Contractor & Admin)
        if old_status != new_status:
            # Notify the Contractor assigned to this Job
            if task.job.assigned_contractor:
                Notification.objects.create(
                    user=task.job.assigned_contractor,
                    message=f"Task Update: '{task.title}' is now {new_status}."
                )
            
            # Notify ALL Admins
            admins = User.objects.filter(userprofile__role='ADMIN')
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    message=f"Task Update: '{task.title}' on job '{task.job.title}' is now {new_status}."
                )

        # 2. Was the Task reassigned to a NEW Electrician?
        if str(old_electrician) != str(task.electrician_id) and task.electrician and task.electrician.user:
            Notification.objects.create(
                user=task.electrician.user,
                message=f"You have been reassigned to Task: {task.title}"
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
    role = request.user.userprofile.role

    # 1. ROLE-BASED DATA FETCHING
    if role == 'ELECTRICIAN':
        # Find the jobs this electrician has tasks for
        jobs = Job.objects.filter(tasks__electrician__user=request.user).distinct()
        # Only show materials linked to those specific jobs
        materials = Material.objects.filter(job__in=jobs).select_related('job')
    elif role == 'CONTRACTOR':
        # Find the jobs this contractor is assigned to
        jobs = Job.objects.filter(assigned_contractor=request.user)
        # Only show materials linked to those specific jobs
        materials = Material.objects.filter(job__in=jobs).select_related('job')
    else:
        # Admins see everything
        jobs = Job.objects.all()
        materials = Material.objects.select_related('job').all()

    # 2. Get filter parameters from the URL
    search_query = request.GET.get('q', '')
    job_filter = request.GET.get('job', '')
    stock_filter = request.GET.get('stock', '')

    # 3. Apply Text Search
    if search_query:
        materials = materials.filter(name__icontains=search_query)

    # 4. Apply Job Filter
    if job_filter:
        materials = materials.filter(job_id=job_filter)

    # 5. Apply Stock Status Filter
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
        'jobs': jobs, # Pass the filtered jobs to the template for the dropdown
    })

@jwt_cookie_required
@role_required(['ADMIN', 'CONTRACTOR'])
def add_material(request):

    role = request.user.userprofile.role

    # 1. ROLE-BASED DATA FETCHING
    if  role == 'CONTRACTOR':
        # Find the jobs this contractor is assigned to
        jobs = Job.objects.filter(assigned_contractor=request.user)
        # Only show materials linked to those specific jobs
        # materials = Material.objects.filter(job__in=jobs).select_related('job')
    else:
        # Admins see everything
        jobs = Job.objects.all()
    # jobs = Job.objects.all()

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
def edit_material(request, id):
    material = get_object_or_404(Material, id=id)
    role = request.user.userprofile.role

    # 1. SECURE THE JOB DROPDOWN
    if role == 'CONTRACTOR':
        jobs = Job.objects.filter(assigned_contractor=request.user)
    else:
        jobs = Job.objects.all()

    if request.method == 'POST':
        # Safely grab the incoming used quantity as an integer
        try:
            new_used_qty = int(request.POST['used_quantity'])
        except ValueError:
            messages.error(request, "Invalid quantity value provided.")
            return redirect('edit_material', id=material.id)

        # ==========================================
        # SECURITY RULES FOR ELECTRICIANS
        # ==========================================
        if role == 'ELECTRICIAN':
            
            # --- NEW: Task Status Validation ---
            # Check if this electrician has an "In Progress" task for this material's Job
            has_active_task = Task.objects.filter(
                job=material.job, 
                electrician__user=request.user, 
                status='In Progress'
            ).exists()

            if not has_active_task:
                messages.error(request, "Error: You can only update materials when your task for this job is marked as 'In Progress'.")
                return redirect('edit_material', id=material.id)
            # -----------------------------------

            # Rule 1: Cannot decrease previous usage
            if new_used_qty < material.used_quantity:
                messages.error(request, f"Error: You cannot decrease usage below {material.used_quantity}. Contact your Contractor to fix errors.")
                return redirect('edit_material', id=material.id)

            # Rule 2: Cannot exceed total inventory
            if new_used_qty > material.quantity:
                messages.error(request, f"Error: Used quantity ({new_used_qty}) cannot exceed total stock ({material.quantity}).")
                return redirect('edit_material', id=material.id)

            # ONLY update the used_quantity field
            material.used_quantity = new_used_qty

        # ==========================================
        # RULES FOR ADMINS & CONTRACTORS
        # ==========================================
        else:
            new_total_qty = int(request.POST['quantity'])

            # Rule: Even Admins shouldn't set used > total
            if new_used_qty > new_total_qty:
                messages.error(request, "Error: Used quantity cannot exceed the total quantity.")
                return redirect('edit_material', id=material.id)

            # Admins & Contractors can update everything
            material.name = request.POST['name']
            material.quantity = new_total_qty
            material.unit = request.POST.get('unit', material.unit) # Fallback to existing if hidden
            material.used_quantity = new_used_qty
            material.job_id = request.POST.get('job', material.job_id) # Fallback to existing if hidden

        # Save the changes
        material.save()
        messages.success(request, "Material updated successfully")
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

    # NEW: Fetch Electrician data if they are an electrician
    electrician = None
    if profile.role == 'ELECTRICIAN':
        electrician = Electrician.objects.filter(user=user).first()

    return render(request, 'profile.html', {
        'user': user,
        'role': profile.role,
        'electrician': electrician # Pass to template
    })

@jwt_cookie_required
@login_required
def update_profile(request):
    user = request.user
    profile = user.userprofile

    if request.method == 'POST':
        # 1. Grab incoming data before saving
        new_username = request.POST.get('username')
        new_phone = request.POST.get('phone')
        new_email = request.POST.get('email')

        # ==========================================
        # VALIDATION 1: PHONE NUMBER
        # ==========================================
        if new_phone:
            # Check format: exactly 10 digits
            if not re.match(r'^\d{10}$', new_phone):
                messages.error(request, "Invalid phone number. It must be exactly 10 digits.")
                return redirect('update_profile') # Ensure this matches your urls.py name
            
            # Check uniqueness in UserProfile (excluding the current user)
            from .models import UserProfile # Ensure this is imported
            if UserProfile.objects.filter(phone=new_phone).exclude(user=user).exists():
                messages.error(request, "This phone number is already registered to another user.")
                return redirect('update_profile')

        # ==========================================
        # VALIDATION 2: FINANCIAL DETAILS (ELECTRICIAN ONLY)
        # ==========================================
        if profile.role == 'ELECTRICIAN':
            upi_id = request.POST.get('upi_id')
            bank_account = request.POST.get('bank_account')
            ifsc_code = request.POST.get('ifsc_code')

            if upi_id and not re.match(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$', upi_id):
                messages.error(request, "Invalid UPI ID format. Example: username@bank")
                return redirect('update_profile')

            if bank_account and not re.match(r'^\d{9,18}$', bank_account):
                messages.error(request, "Invalid Bank Account. It must contain 9 to 18 numbers only.")
                return redirect('update_profile')

            if ifsc_code and not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc_code.upper()):
                messages.error(request, "Invalid IFSC code. It must be 11 characters (e.g., SBIN0001234).")
                return redirect('update_profile')

        # ==========================================
        # ALL VALIDATIONS PASSED -> SAVE TO DATABASE
        # ==========================================
        user.username = new_username
        profile.phone = new_phone
        user.email = new_email

        # Handle profile picture upload
        profile_pic = request.FILES.get('profile_picture')
        if profile_pic:
            profile.profile_picture = profile_pic

        user.save()
        profile.save()

        # SAVE FINANCIAL DETAILS
        if profile.role == 'ELECTRICIAN':
            electrician = Electrician.objects.filter(user=user).first()
            if electrician:
                electrician.upi_id = request.POST.get('upi_id')
                electrician.bank_account = request.POST.get('bank_account')
                # Save IFSC code as uppercase for database consistency
                electrician.ifsc_code = request.POST.get('ifsc_code').upper() if request.POST.get('ifsc_code') else None
                electrician.save()

        messages.success(request, "Profile updated successfully")
        return redirect('profile')

    # Fetch to pre-fill the form (GET request)
    electrician = None
    if profile.role == 'ELECTRICIAN':
        electrician = Electrician.objects.filter(user=user).first()

    return render(request, 'update_profile.html', {
        'user': user,
        'profile': profile,
        'electrician': electrician # Pass to template
    })


# -------------------- REPORTS --------------------
@jwt_cookie_required
def reports_page(request):
    role = request.user.userprofile.role

    # 1. TIMEZONE-SAFE DATE (Ensures late-night tasks log correctly)
    today = timezone.localtime(timezone.now()).date()

    # ==========================================
    # 2. SECURE DATA FENCING BY ROLE
    # ==========================================
    if role == 'CONTRACTOR':
        # Fenced queries: Only grab data linked to this specific contractor
        base_tasks = Task.objects.filter(job__assigned_contractor=request.user)
        base_jobs = Job.objects.filter(assigned_contractor=request.user)
        base_materials = Material.objects.filter(job__assigned_contractor=request.user)
        electricians_count = Electrician.objects.filter(
            tasks__job__assigned_contractor=request.user
        ).distinct().count()
    else:
        # Admin View: Unrestricted
        base_tasks = Task.objects.all()
        base_jobs = Job.objects.all()
        base_materials = Material.objects.all()
        electricians_count = Electrician.objects.count()

    # ==========================================
    # 3. REPORT CALCULATIONS (The Bug Fixes)
    # ==========================================
    
    # FIX 1: Use updated_at so it captures ANY work done today!
    tasks_today = base_tasks.filter(updated_at__date=today)
    
    # FIX 2: Order completed tasks by most recent so old ones don't clog the top
    completed_tasks = base_tasks.filter(status='Completed').order_by('-updated_at')[:10] 

    # Activity breakdown
    activity = base_tasks.values('electrician__name').annotate(count=Count('id'))

    context = {
        'electricians': electricians_count,
        'jobs': base_jobs.count(),
        'tasks': base_tasks.count(),
        'materials': base_materials.count(),

        'pending': base_tasks.filter(status='Pending').count(),
        'in_progress': base_tasks.filter(status='In Progress').count(),
        'completed': base_tasks.filter(status='Completed').count(),

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
    request.session['impersonation_return_url'] = 'electricians'

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


# -------------------- SETTLEMENTS & EARNINGS --------------------
@jwt_cookie_required
@role_required(['ADMIN'])
def admin_settlement_dashboard(request):
    # Fetch all payments that are still Pending
    pending_payments = TaskPayment.objects.filter(status='PENDING').select_related('task', 'electrician')
    paid_payments = TaskPayment.objects.filter(status='PAID').order_by('-paid_at')
    
    context = {
        'pending_payments': pending_payments,
        'paid_payments': paid_payments
    }
    return render(request, 'admin_settlements.html', context)

def process_payment(request, payment_id):
    if request.method == "POST":
        payment = TaskPayment.objects.get(id=payment_id)
        settled_amount = request.POST.get('amount')
        
        # --- NEW: Backend validation for negative or zero amounts ---
        if float(settled_amount) <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return redirect('admin_settlement_dashboard')
        
        payment.amount = settled_amount
        payment.status = 'PAID'
        payment.paid_at = timezone.now()
        payment.save()
        
        messages.success(request, f"Payment of ₹{settled_amount} settled successfully.")
        return redirect('admin_settlement_dashboard')

@jwt_cookie_required    
@login_required(login_url='login')
def electrician_earnings(request):
    # Filter payments strictly by the logged-in electrician
    my_payments = TaskPayment.objects.filter(electrician=request.user).select_related('task')
    
    # Calculate totals for their dashboard
    total_earned = sum(p.amount for p in my_payments if p.status == 'PAID' and p.amount)
    
    context = {
        'my_payments': my_payments,
        'total_earned': total_earned
    }
    return render(request, 'electrician_earnings.html', context)

