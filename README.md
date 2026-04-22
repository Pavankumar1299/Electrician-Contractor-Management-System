# ⚡ Electrician Contractor Management System

A full-stack web application designed to manage electricians, contractors, and job workflows efficiently.
It includes authentication, task tracking, notifications, and dashboard analytics.

---

## 🚀 Features

* 🔐 JWT-based Authentication (Login / Register)
* 👷 Electrician Management
* 📋 Job Assignment & Tracking
* ✅ Task Management System
* 🔔 Notification System (Role-based)
* 📊 Dashboard with Real-time Statistics

---

## 🛠️ Tech Stack

### 🔹 Backend

* Django
* Django REST Framework
* SimpleJWT

### 🔹 Frontend

* HTML
* CSS
* Bootstrap
* JavaScript

### 🔹 Database

* SQLite

---

## 📸 Screenshots

### 🏠 Home Page

<img src="screenshots/index.png" width="50%">

### 🔐 Login Page

<img src="screenshots/login.png" width="50%">

### 📝 Register Page

<img src="screenshots/register.png" width="50%">

---

### 📊 Dashboard

#### Admin Dashboard

<img src="screenshots/admin_dashboard.png" width="50%">

#### Electrician Dashboard

<img src="screenshots/ele_dashboard.png" width="50%">

---

### 👷 Electricians Page

<img src="screenshots/electricians.png" width="50%">

---

### 👷 View as Electrician

<img src="screenshots/view_as.png" width="50%">

---

### 💼 Jobs Page

<img src="screenshots/jobs.png" width="50%">
<img src="screenshots/create_job.png" width="50%">

---

### ✅ Tasks Page

<img src="screenshots/tasks.png" width="50%">
<img src="screenshots/create_task.png" width="50%">
<img src="screenshots/edit_task.png" width="50%">
<img src="screenshots/ele_tasks.png" width="50%">

---

### 🔔 Notification Page

<img src="screenshots/admin_notify.png" width="50%">
<img src="screenshots/ele_notify.png" width="50%">

---

### 📈 Reports Page

<img src="screenshots/reports.png" width="50%">

---

### 👤 Profile Page

<img src="screenshots/profile.png" width="50%">

---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Pavankumar1299/Electrician-Contractor-Management-System.git
cd Electrician-Contractor-Management-System/backend
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Apply Migrations

```bash
python manage.py migrate
```

---

### 5️⃣ Run Server

```bash
python manage.py runserver
```

---

## 🔑 Authentication (JWT)

After login, you will receive a JWT token.

Use it in requests:

```
Authorization: Bearer <your_token>
```

---

## 🎯 Future Improvements

* 🔔 Real-time notifications (WebSockets)
* 📱 Responsive UI enhancements
* ☁️ Deployment (AWS / Render)
* 📊 Advanced analytics dashboard
* 🔒 Improved role-based permissions

---

⭐ If you like this project, consider giving it a star on GitHub!
