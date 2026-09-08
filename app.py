import sqlite3
import uuid
import random
import csv
import io
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = "abdm_secure_secret_key"
DB_NAME = "database.db"

# BHASHINI API CONFIGURATION
BHASHINI_API_URL = "https://dhruva-api.bhashini.gov.in/services/inference/translation"
BHASHINI_API_KEY = "YOUR_BHASHINI_API_KEY"

# ABDM Fallback Directory
ABDM_HOSPITALS = [
    "Central District Hospital",
    "City General Hospital",
    "Apollo Health Institute",
    "Fortis Care Center",
    "AIIMS Speciality Clinic",
    "Sunshine Community Hospital",
    "Metropolitan Medical Center"
]

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode=WAL;')
    
    # Patients Table (ABHA Users)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abha_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            dob TEXT NOT NULL,
            mobile TEXT NOT NULL,
            photo_url TEXT DEFAULT 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150',
            current_hospital TEXT DEFAULT 'Central District Hospital'
        )
    ''')
    
    # Hospitals & Facilities Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hfr_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Seed default hospitals if empty
    cursor.execute('SELECT COUNT(*) FROM hospitals')
    if cursor.fetchone()[0] == 0:
        default_hospitals = [
            ("IN3310000001", "Central District Hospital", "Kolkata", "West Bengal", "hosp123"),
            ("IN3310000002", "City General Hospital", "Asansol", "West Bengal", "hosp123"),
            ("IN3310000003", "Apollo Health Institute", "Durgapur", "West Bengal", "hosp123"),
            ("IN3310000004", "Fortis Care Center", "Siliguri", "West Bengal", "hosp123")
        ]
        cursor.executemany(
            'INSERT INTO hospitals (hfr_id, name, city, state, password) VALUES (?, ?, ?, ?, ?)',
            default_hospitals
        )

    # Health Conditions Table (Supports Translations, Dates & Doctor Feedback)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_abha TEXT NOT NULL,
            problem_type TEXT NOT NULL,
            original_text TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            language TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            doctor_suggestion TEXT DEFAULT 'Awaiting doctor consultation.',
            doctor_name TEXT DEFAULT 'N/A',
            hospital_name TEXT DEFAULT 'N/A',
            FOREIGN KEY (patient_abha) REFERENCES patients (abha_id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# --- AUTHENTICATION & NAVIGATION ---

@app.route('/')
def main_portal():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'send_otp':
            abha_input = request.form.get('abha_input')
            if not abha_input:
                return render_template('login.html', otp_sent=False, error="Please enter a valid ABHA ID or Mobile Number.")
            
            session['temp_abha'] = abha_input
            session['otp_sent'] = True
            return render_template('login.html', otp_sent=True, abha_input=abha_input, message="OTP sent successfully (Mock OTP: 123456)")
        
        elif action == 'verify_otp':
            entered_otp = request.form.get('otp')
            abha_input = session.get('temp_abha')
            
            if entered_otp == '123456' and abha_input:
                conn = get_db()
                # Check if patient exists by ABHA ID or Mobile number
                patient = conn.execute(
                    'SELECT * FROM patients WHERE abha_id = ? OR mobile = ?', 
                    (abha_input, abha_input)
                ).fetchone()
                
                # If patient doesn't exist yet, auto-create account using the mobile/input
                if not patient:
                    abha_address = abha_input if '@' in abha_input else f"{abha_input}@abdm"
                    with conn:
                        conn.execute(
                            'INSERT INTO patients (abha_id, name, gender, dob, mobile, current_hospital) VALUES (?, ?, ?, ?, ?, ?)',
                            (abha_address, 'Patient User', 'Male', '1995-01-01', abha_input, 'Central District Hospital')
                        )
                    patient = conn.execute('SELECT * FROM patients WHERE abha_id = ?', (abha_address,)).fetchone()
                
                conn.close()
                
                # Set active session to the verified ABHA ID
                session['user'] = patient['abha_id']
                session['user_type'] = 'patient'
                session.pop('temp_abha', None)
                session.pop('otp_sent', None)
                
                return redirect(url_for('patient_dashboard'))
            else:
                return render_template('login.html', otp_sent=True, abha_input=abha_input, error="Invalid OTP. Use 123456.")

    return render_template('login.html', otp_sent=False)

@app.route('/hospital-login', methods=['GET', 'POST'])
def hospital_login():
    if request.method == 'POST':
        hfr_id = request.form.get('hfr_id')
        password = request.form.get('password')
        conn = get_db()
        hosp = conn.execute('SELECT * FROM hospitals WHERE hfr_id = ? AND password = ?', (hfr_id, password)).fetchone()
        conn.close()
        if hosp:
            session['user'] = hfr_id
            session['user_type'] = 'hospital'
            return redirect(url_for('hospital_dashboard'))
        else:
            return render_template('hospital_login.html', error="Invalid Health Facility ID or password.")
    return render_template('hospital_login.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_id = request.form.get('admin_id')
        password = request.form.get('password')
        if admin_id == 'admin' and password == 'admin123':
            session['user'] = admin_id
            session['user_type'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid Admin credentials. (Use: admin / admin123)")
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- ABHA CREATION ---

@app.route('/abha-creation', methods=['GET', 'POST'])
def abha_creation():
    if request.method == 'POST':
        name = request.form.get('name')
        gender = request.form.get('gender')
        dob = request.form.get('dob')
        mobile = request.form.get('mobile')
        
        if not name or not gender or not dob or not mobile:
            return render_template('abha_creation.html', error="All fields are required.")

        abha_number = f"91-{random.randint(1000,9999)}-{random.randint(1000,9999)}-{random.randint(1000,9999)}"
        abha_address = f"{mobile}@abdm"

        conn = get_db()
        try:
            with conn:
                conn.execute(
                    'INSERT INTO patients (abha_id, name, gender, dob, mobile) VALUES (?, ?, ?, ?, ?)',
                    (abha_address, name, gender, dob, mobile)
                )
            conn.close()
            
            # Set session directly to newly created account
            session['user'] = abha_address
            session['user_type'] = 'patient'
            
            return render_template(
                'abha_creation.html', 
                success=True, 
                abha_number=abha_number, 
                abha_address=abha_address, 
                name=name, 
                gender=gender, 
                dob=dob, 
                mobile=mobile
            )
            
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('abha_creation.html', error=f"An account with mobile ({mobile}) already exists. Please log in.")

    return render_template('abha_creation.html')

# --- PATIENT DASHBOARD & ACTIONS ---

@app.route('/patient-dashboard')
def patient_dashboard():
    if 'user' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    
    abha_id = session['user']
    selected_date = request.args.get('visit_date', datetime.now().strftime("%Y-%m-%d"))
    
    conn = get_db()
    patient = conn.execute('SELECT * FROM patients WHERE abha_id = ?', (abha_id,)).fetchone()
    
    if not patient:
        conn.close()
        session.clear()
        return redirect(url_for('login'))

    db_hospitals = [row['name'] for row in conn.execute('SELECT name FROM hospitals').fetchall()]
    hospital_list = db_hospitals if db_hospitals else ABDM_HOSPITALS

    visit_dates = conn.execute('SELECT DISTINCT visit_date FROM patient_problems WHERE patient_abha = ? ORDER BY visit_date DESC', (abha_id,)).fetchall()
    problems = conn.execute('SELECT * FROM patient_problems WHERE patient_abha = ? AND visit_date = ? ORDER BY id DESC', (abha_id, selected_date)).fetchall()
    
    is_date_frozen = len(problems) > 0 and selected_date != datetime.now().strftime("%Y-%m-%d")

    conn.close()
    return render_template(
        'patient_dashboard.html', 
        patient=patient, 
        problems=problems, 
        hospital_list=hospital_list, 
        visit_dates=visit_dates, 
        selected_date=selected_date, 
        is_date_frozen=is_date_frozen
    )

@app.route('/update-hospital', methods=['POST'])
def update_hospital():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    hospital_name = request.json.get('hospital_name')
    abha_id = session['user']
    
    if hospital_name:
        conn = get_db()
        with conn:
            conn.execute('UPDATE patients SET current_hospital = ? WHERE abha_id = ?', (hospital_name, abha_id))
        conn.close()
        return jsonify({'status': 'SUCCESS', 'hospital': hospital_name})
    
    return jsonify({'error': 'Invalid hospital selection.'}), 400

@app.route('/add-problem', methods=['POST'])
def add_problem():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    patient_abha = session['user']
    problem_type = request.form.get('problem_type')
    original_text = request.form.get('description')
    source_lang = request.form.get('language', 'hi')
    visit_date = request.form.get('visit_date', datetime.now().strftime("%Y-%m-%d"))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if not original_text or not problem_type:
        return redirect(url_for('patient_dashboard', visit_date=visit_date))

    translated_text = original_text
    if source_lang != 'en':
        if BHASHINI_API_KEY == "YOUR_BHASHINI_API_KEY":
            translated_text = f"[English Translation]: {original_text}"
        else:
            try:
                payload = {
                    "pipelineTasks": [{"taskType": "translation", "config": {"language": {"sourceLanguage": source_lang, "targetLanguage": "en"}}}],
                    "inputData": {"input": [{"source": original_text}]}
                }
                headers = {"Authorization": BHASHINI_API_KEY, "Content-Type": "application/json"}
                response = requests.post(BHASHINI_API_URL, json=payload, headers=headers)
                translated_text = response.json()['pipelineResponse'][0]['output'][0]['target']
            except Exception:
                translated_text = original_text

    conn = get_db()
    try:
        with conn:
            conn.execute(
                'INSERT INTO patient_problems (patient_abha, problem_type, original_text, translated_text, language, recorded_at, visit_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (patient_abha, problem_type, original_text, translated_text, source_lang, timestamp, visit_date)
            )
    except sqlite3.OperationalError as e:
        print(f"Database Write Error: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('patient_dashboard', visit_date=visit_date))

@app.route('/hospital/add-suggestion', methods=['POST'])
def add_doctor_suggestion():
    if 'user' not in session or session.get('user_type') != 'hospital':
        return redirect(url_for('hospital_login'))

    problem_id = request.form.get('problem_id')
    doctor_suggestion = request.form.get('doctor_suggestion')
    doctor_name = request.form.get('doctor_name')
    hfr_id = session['user']

    conn = get_db()
    hosp = conn.execute('SELECT name FROM hospitals WHERE hfr_id = ?', (hfr_id,)).fetchone()
    hospital_name = hosp['name'] if hosp else "Network Hospital"

    with conn:
        conn.execute('''
            UPDATE patient_problems 
            SET doctor_suggestion = ?, doctor_name = ?, hospital_name = ?
            WHERE id = ?
        ''', (doctor_suggestion, doctor_name, hospital_name, problem_id))

    conn.close()
    return redirect(url_for('hospital_dashboard'))

# --- CLINICAL PORTAL & DOCTOR ADVICE ---

@app.route('/hospital-dashboard')
def hospital_dashboard():
    if 'user' not in session or session.get('user_type') != 'hospital':
        return redirect(url_for('hospital_login'))
        
    hfr_id = session['user']
    conn = get_db()
    
    # 1. Retrieve current logged-in hospital details
    hosp = conn.execute('SELECT * FROM hospitals WHERE hfr_id = ?', (hfr_id,)).fetchone()
    hospital_name = hosp['name'] if hosp else "Central District Hospital"
    
    # 2. Fetch ONLY patients whose current_hospital matches this hospital's name
    patients = conn.execute(
        'SELECT * FROM patients WHERE current_hospital = ?', 
        (hospital_name,)
    ).fetchall()
    
    # 3. Fetch health records ONLY for patients currently registered to this hospital
    # includes full historical notes/suggestions from prior facilities
    patient_records = conn.execute('''
        SELECT 
            pp.id, 
            p.name, 
            p.abha_id, 
            p.current_hospital, 
            pp.problem_type, 
            pp.original_text, 
            pp.translated_text, 
            pp.recorded_at, 
            pp.visit_date, 
            pp.doctor_suggestion, 
            pp.doctor_name, 
            pp.hospital_name AS treating_hospital
        FROM patients p
        INNER JOIN patient_problems pp ON p.abha_id = pp.patient_abha
        WHERE p.current_hospital = ?
        ORDER BY pp.id DESC
    ''', (hospital_name,)).fetchall()
    
    conn.close()
    return render_template(
        'index.html', 
        patients=patients, 
        patient_records=patient_records, 
        hospital_name=hospital_name, 
        hfr_id=hfr_id
    )

# --- ADMIN CONSOLE ENDPOINTS ---

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    conn = get_db()
    patient_count = conn.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
    records_count = conn.execute('SELECT COUNT(*) FROM patient_problems').fetchone()[0]
    hospital_count = conn.execute('SELECT COUNT(*) FROM hospitals').fetchone()[0]
    
    patients = conn.execute('SELECT * FROM patients ORDER BY id DESC').fetchall()
    hospitals = conn.execute('SELECT * FROM hospitals ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template(
        'admin_dashboard.html', 
        patient_count=patient_count, 
        records_count=records_count, 
        hospital_count=hospital_count, 
        patients=patients,
        hospitals=hospitals,
        user=session['user']
    )

@app.route('/admin/add-hospital', methods=['POST'])
def admin_add_hospital():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    hfr_id = request.form.get('hfr_id')
    name = request.form.get('name')
    city = request.form.get('city')
    state = request.form.get('state')
    password = request.form.get('password', 'hosp123')
    
    conn = get_db()
    try:
        with conn:
            conn.execute('INSERT INTO hospitals (hfr_id, name, city, state, password) VALUES (?, ?, ?, ?, ?)', (hfr_id, name, city, state, password))
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-hospital', methods=['POST'])
def admin_update_hospital():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    hfr_id = request.form.get('hfr_id')
    name = request.form.get('name')
    city = request.form.get('city')
    state = request.form.get('state')
    password = request.form.get('password')
    
    conn = get_db()
    with conn:
        conn.execute('UPDATE hospitals SET name=?, city=?, state=?, password=? WHERE hfr_id=?', (name, city, state, password, hfr_id))
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-hospital', methods=['POST'])
def admin_delete_hospital():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    hfr_id = request.form.get('hfr_id')
    if hfr_id:
        conn = get_db()
        with conn:
            conn.execute('DELETE FROM hospitals WHERE hfr_id = ?', (hfr_id,))
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk-upload-hospitals', methods=['POST'])
def admin_bulk_upload_hospitals():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    file = request.files.get('file')
    if file and file.filename.endswith('.csv'):
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        conn = get_db()
        with conn:
            for row in csv_input:
                hfr_id = row.get('hfr_id')
                name = row.get('name')
                city = row.get('city', 'Unknown')
                state = row.get('state', 'Unknown')
                password = row.get('password', 'hosp123')
                if hfr_id and name:
                    conn.execute('''
                        INSERT INTO hospitals (hfr_id, name, city, state, password)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(hfr_id) DO UPDATE SET name=excluded.name, city=excluded.city, state=excluded.state, password=excluded.password
                    ''', (hfr_id, name, city, state, password))
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-patient', methods=['POST'])
def admin_add_patient():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    name = request.form.get('name')
    gender = request.form.get('gender')
    dob = request.form.get('dob')
    mobile = request.form.get('mobile')
    current_hospital = request.form.get('current_hospital', 'Central District Hospital')
    abha_id = f"{mobile}@abdm"

    conn = get_db()
    try:
        with conn:
            conn.execute('INSERT INTO patients (abha_id, name, gender, dob, mobile, current_hospital) VALUES (?, ?, ?, ?, ?, ?)', (abha_id, name, gender, dob, mobile, current_hospital))
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-patient', methods=['POST'])
def admin_update_patient():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    abha_id = request.form.get('abha_id')
    name = request.form.get('name')
    gender = request.form.get('gender')
    dob = request.form.get('dob')
    mobile = request.form.get('mobile')
    current_hospital = request.form.get('current_hospital')
    
    conn = get_db()
    with conn:
        conn.execute('UPDATE patients SET name=?, gender=?, dob=?, mobile=?, current_hospital=? WHERE abha_id=?', (name, gender, dob, mobile, current_hospital, abha_id))
    conn.close()
    return redirect(url_for('admin_dashboard'))

# UPDATED DELETION ROUTE: Safely processes ABHA IDs via POST body data
@app.route('/admin/delete-patient', methods=['POST'])
def admin_delete_patient():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    abha_id = request.form.get('abha_id')
    
    if abha_id:
        conn = get_db()
        with conn:
            conn.execute('DELETE FROM patients WHERE abha_id = ?', (abha_id,))
            conn.execute('DELETE FROM patient_problems WHERE patient_abha = ?', (abha_id,))
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bulk-upload-patients', methods=['POST'])
def admin_bulk_upload_patients():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))
        
    file = request.files.get('file')
    if file and file.filename.endswith('.csv'):
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        conn = get_db()
        with conn:
            for row in csv_input:
                mobile = row.get('mobile')
                name = row.get('name')
                gender = row.get('gender', 'Male')
                dob = row.get('dob', '1990-01-01')
                current_hospital = row.get('current_hospital', 'Central District Hospital')
                abha_id = row.get('abha_id', f"{mobile}@abdm")
                
                if abha_id and name:
                    conn.execute('''
                        INSERT INTO patients (abha_id, name, gender, dob, mobile, current_hospital)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(abha_id) DO UPDATE SET name=excluded.name, gender=excluded.gender, dob=excluded.dob, mobile=excluded.mobile, current_hospital=excluded.current_hospital
                    ''', (abha_id, name, gender, dob, mobile, current_hospital))
        conn.close()
    return redirect(url_for('admin_dashboard'))
    
# Place this at the VERY BOTTOM of app.py (after def init_db() and all routes)
if __name__ == '__main__':
    init_db()  # Database initializes only after function definitions are parsed
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)