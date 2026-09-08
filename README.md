# ABDM Health Record & Facility Management System

A compliant web application built for the **Ayushman Bharat Digital Mission (ABDM)** hackathon demonstration. This multi-role system bridges **Patients (ABHA users)**, **Hospitals (HIP/HIU Facilities)**, and **Administrative Controllers (NHA Master Registry)**.

---

## 🌟 Key Features

* **Patient Portal (ABHA User)**
  * OTP-based authentication using ABHA ID or registered mobile numbers (Mock OTP: `123456`).
  * Instant ABHA ID generation with card view (`<mobile>@abdm`).
  * Dynamic hospital selection and location switching via dropdown or simulated QR code scanner.
  * Multilingual health symptom entry (supports English, Hindi, Bengali, Tamil, Telugu) with Web Speech API integration (voice-to-text with editable output).
  * Date-wise historical visit record tracking with automatic read-only freezing for past visit dates.
  * Full visibility into attending doctor advice, doctor names, and facility details across past visits.

* **Clinical Portal (Hospital / HIP)**
  * Secure authentication for registered network facilities using Health Facility Registry (HFR) credentials.
  * **Strict Data Scoping**: Clinicians view and manage only patient cases currently assigned to their specific facility.
  * Access to the complete historical medical timeline, preserving consultation notes written by doctors at previous treating facilities.
  * Interface to append doctor names, diagnostic notes, and prescriptions directly to patient case records.

* **Admin Console (NHA Master Registry)**
  * High-level metric dashboards for patient counts, registered facilities, and record entries.
  * Full CRUD (Create, Read, Update, Delete) management for both **ABHA Patients** and **Network Hospitals**.
  * Bulk onboarding of hospitals and patients using standard CSV file uploads.
  * Credential management and instant password resets for facility logins.
  * Safe POST-payload deletion handling for ABHA addresses containing `@` symbols.

---

## 📁 System Architecture & Tech Stack

* **Backend Framework**: Python (Flask)
* **Database Engine**: SQLite3 configured with Write-Ahead Logging (`WAL`) mode and 30-second connection timeout handling for optimal concurrency.
* **Frontend UI**: HTML5, Tailwind CSS, JavaScript (Vanilla ES6), Html5Qrcode, and Web Speech API.
* **Translation Service Integration**: Bhashini API pipeline support (with built-in fallback handling).

---

## 🗄️ Database Schema

### 1. `patients`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | System identifier |
| `abha_id` | TEXT | UNIQUE, NOT NULL | ABHA address (e.g., `8926935233@abdm`) |
| `name` | TEXT | NOT NULL | Patient full name |
| `gender` | TEXT | NOT NULL | Male / Female / Other |
| `dob` | TEXT | NOT NULL | Date of birth (`YYYY-MM-DD`) |
| `mobile` | TEXT | NOT NULL | Registered 10-digit mobile number |
| `photo_url` | TEXT | DEFAULT | Profile display photo URL |
| `current_hospital` | TEXT | DEFAULT | Currently associated hospital name |

### 2. `hospitals`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Facility record ID |
| `hfr_id` | TEXT | UNIQUE, NOT NULL | Health Facility Registry ID (e.g., `IN3310000001`) |
| `name` | TEXT | NOT NULL | Facility display name |
| `city` | TEXT | NOT NULL | Facility city |
| `state` | TEXT | NOT NULL | Facility state |
| `password` | TEXT | NOT NULL | Facility portal login password |

### 3. `patient_problems`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Encounter entry ID |
| `patient_abha` | TEXT | FOREIGN KEY (`patients.abha_id`) | Associated patient ABHA |
| `problem_type` | TEXT | NOT NULL | Issue category |
| `original_text` | TEXT | NOT NULL | Regional/spoken symptom description |
| `translated_text` | TEXT | NOT NULL | English translation output |
| `language` | TEXT | NOT NULL | Input language code (`hi`, `bn`, `ta`, `te`, `en`) |
| `recorded_at` | TEXT | NOT NULL | Timestamp (`YYYY-MM-DD HH:MM`) |
| `visit_date` | TEXT | NOT NULL | Date of encounter (`YYYY-MM-DD`) |
| `doctor_suggestion`| TEXT | DEFAULT | Doctor's diagnostic advice |
| `doctor_name` | TEXT | DEFAULT | Attending clinician name |
| `hospital_name` | TEXT | DEFAULT | Facility name where consultation occurred |

---

## 🚀 Getting Started

### Prerequisites
* Python 3.8 or higher installed.

### Setup & Execution

1. **Setup Project Directory**:
   Ensure `app.py` and the `templates/` folder (`home.html`, `login.html`, `abha_creation.html`, `patient_dashboard.html`, `hospital_login.html`, `index.html`, `admin_login.html`, `admin_dashboard.html`) are in the root directory.

2. **Launch Application**:
   ```bash
   python app.py

The database database.db will automatically initialize with default seeds upon first startup.

Access Portals:

Main Landing: http://127.0.0.1:5000/

Patient Login: http://127.0.0.1:5000/login (Mock OTP: 123456)

Hospital Login: http://127.0.0.1:5000/hospital-login (Default HFR: IN3310000001 / Pass: hosp123)

Admin Login: http://127.0.0.1:5000/admin-login (Credentials: admin / admin123)

📄 Bulk Upload CSV Standards
Hospital Bulk Upload (hospitals.csv)
Code snippet
hfr_id,name,city,state,password
IN3310000005,Sunrise Hospital,Kolkata,West Bengal,sun123
IN3310000006,Desun Hospital,Siliguri,West Bengal,desun123
ABHA User Bulk Upload (patients.csv)
Code snippet
abha_id,name,gender,dob,mobile,current_hospital
9876543210@abdm,Amit Roy,Male,1992-05-14,9876543210,Central District Hospital
8765432109@abdm,Sujata Sen,Female,1998-10-20,8765432109,City General Hospital
⚠️ Hackathon Disclaimer
Note: This application is a sandbox demonstration prototype built for hackathon evaluation and technical presentation. It utilizes simulated OTP mechanisms and local SQLite storage, operating independently of official NHA production servers.
