# 🏥 HealthAI – Smart Healthcare Management System



Live Demo URL  : https://ai-healthcare-portal.onrender.com
HealthAI is a comprehensive Healthcare Management System designed to streamline hospital operations, patient management, doctor scheduling, electronic health records, resource allocation, and disease prediction using Machine Learning.

The system provides separate portals for Administrators, Doctors, and Patients, enabling efficient healthcare management through an intuitive web interface.

---

# 📌 Project Overview

Healthcare organizations often struggle with managing patient records, appointments, medical resources, and administrative tasks efficiently.

HealthAI addresses these challenges by providing:

- Centralized patient management
- Appointment scheduling and tracking
- Electronic Health Records (EHR)
- Hospital bed management
- Resource allocation monitoring
- Disease risk prediction using Machine Learning
- Dashboard analytics and reporting
- PDF report generation

---

# 🚀 Features

## 👨‍💼 Admin Portal

- Secure Admin Authentication
- Dashboard Analytics
- Patient Management
- Doctor Management
- Staff Management
- Appointment Monitoring
- Hospital Resource Tracking
- Bed Allocation Management
- PDF Report Generation

---

## 👨‍⚕️ Doctor Portal

- Doctor Login
- View Assigned Patients
- Access Patient Medical Records
- Update Diagnoses
- Manage Treatment History
- Review Appointment Schedule

---

## 👤 Patient Portal

- Patient Registration
- Secure Login
- Book Appointments
- View Medical Records
- Access Prescription History
- Track Treatment Progress

---

## 📅 Appointment Management

- Schedule Appointments
- Doctor Availability Tracking
- Appointment History
- Follow-up Management
- Status Monitoring

---

## 📋 Electronic Health Records (EHR)

- Patient Diagnoses
- Prescriptions
- Lab Reports
- Treatment History
- Visit Records

---

## 🛏️ Bed Management

- Real-time Bed Availability
- ICU Bed Tracking
- Ward Allocation
- Occupancy Monitoring

---

## 🏥 Resource Management

- Medical Equipment Tracking
- Inventory Monitoring
- Resource Utilization Analytics
- Availability Status Updates

---

## 🤖 Machine Learning Disease Prediction

The system incorporates Machine Learning models to predict disease risks based on patient health parameters.

### Supported Predictions

- Diabetes Risk Prediction
- Heart Disease Risk Prediction
- Kidney Disease Risk Prediction

### ML Technologies

- Scikit-Learn
- Pandas
- NumPy
- Joblib

---

## 📄 PDF Reporting System

Generate professional reports for:

- Patients
- Doctors
- Appointments
- Resources
- Hospital Statistics

---

# 🛠️ Technology Stack

## Backend

- Python
- Flask
- SQLite
- REST APIs

## Frontend

- HTML5
- CSS3
- JavaScript

## Machine Learning

- Scikit-Learn
- NumPy
- Pandas
- Joblib

## Reporting

- ReportLab

## Deployment

- Render
- Gunicorn

---

# 📂 Project Structure

```text
healthcare_system/
│
├── backend/
│   ├── app.py
│   └── __init__.py
│
├── database/
│   ├── healthcare.db
│   └── init_db.py
│
├── frontend/
│   ├── index.html
│   ├── dashboard.html
│   ├── appointments.html
│   ├── patients.html
│   ├── staff.html
│   ├── beds.html
│   ├── resources.html
│   ├── ehr.html
│   ├── predict.html
│   ├── doctor_login.html
│   ├── doctor_dashboard.html
│   └── static/
│       └── style.css
│
├── ml_models/
│   ├── train_models.py
│   └── saved_models/
│
├── render_start.py
├── render.yaml
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation Guide

## Step 1: Clone Repository

```bash
git clone https://github.com/your-username/healthai.git
cd healthai
```

## Step 2: Create Virtual Environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux/Mac

```bash
source venv/bin/activate
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4: Initialize Database

```bash
python database/init_db.py
```

---

## Step 5: Train Machine Learning Models

```bash
python ml_models/train_models.py
```

---

## Step 6: Run Application

```bash
python backend/app.py
```

Application will start at:

```text
http://127.0.0.1:5000
```

---

# 🔐 Demo Credentials

## Admin Login

```text
Username: admin
Password: admin123
```

---

## Doctor Login

```text
Username: doctor1
Password: doc123
```

```text
Username: doctor2
Password: doc223
```

```text
Username: doctor3
Password: doc323
```

---

## Patient Login

```text
Username: patient1
Password: pat123
```

---

# 📊 Database Tables

The application uses SQLite with the following tables:

- users
- patients
- doctors
- staff
- appointments
- ehr
- beds
- resources
- predictions
- notifications

---

# 🌐 Deployment on Render

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn render_start:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

---

# 🔮 Future Enhancements

- JWT Authentication
- Email Notifications
- SMS Appointment Alerts
- AI Chatbot Assistant
- Telemedicine Integration
- Cloud Database (PostgreSQL)
- Role-Based Access Control
- Real-Time Analytics Dashboard
- Mobile Application

---

# 📈 Learning Outcomes

This project demonstrates:

- Full Stack Web Development
- Flask Backend Development
- Database Design and Management
- Machine Learning Integration
- REST API Development
- Healthcare Workflow Automation
- Cloud Deployment using Render

---

# 👨‍💻 Author

**Sameera**

Healthcare Management System with Machine Learning

---

# 📄 License

This project is developed for educational and learning purposes.
