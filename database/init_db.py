import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "healthcare.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'patient',
        email TEXT DEFAULT '',
        name  TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        age INTEGER DEFAULT 0,
        gender TEXT DEFAULT '',
        weight REAL DEFAULT 0,
        height REAL DEFAULT 0,
        blood_group TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        medical_conditions TEXT DEFAULT '',
        allergies TEXT DEFAULT '',
        family_history TEXT DEFAULT '',
        insurance TEXT DEFAULT '',
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        department TEXT DEFAULT 'General',
        specialization TEXT DEFAULT '',
        experience INTEGER DEFAULT 0,
        qualification TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        status TEXT DEFAULT 'On Shift',
        available_slots TEXT DEFAULT '9AM,11AM,2PM,4PM',
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT DEFAULT 'nurse',
        department TEXT DEFAULT '',
        shift TEXT DEFAULT 'Morning',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        qualification TEXT DEFAULT '',
        experience INTEGER DEFAULT 0,
        on_leave INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        appointment_date TEXT,
        time_slot TEXT,
        type TEXT DEFAULT 'Regular Checkup',
        status TEXT DEFAULT 'pending',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id)  REFERENCES doctors(id)
    );

    CREATE TABLE IF NOT EXISTS ehr (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        diagnosis TEXT DEFAULT '',
        prescription TEXT DEFAULT '',
        lab_reports TEXT DEFAULT '',
        treatment_history TEXT DEFAULT '',
        visit_date TEXT,
        doctor_id INTEGER DEFAULT 1,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );

    CREATE TABLE IF NOT EXISTS beds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ward TEXT DEFAULT 'General Ward',
        bed_number TEXT,
        bed_type TEXT DEFAULT 'General',
        status TEXT DEFAULT 'available',
        patient_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_name TEXT,
        resource_type TEXT,
        total INTEGER DEFAULT 0,
        available INTEGER DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        disease_type TEXT,
        risk_score REAL,
        predicted_disease TEXT,
        severity TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ── Seed demo data ────────────────────────────────────────────────────────
    try:
        # Users
        c.execute("INSERT INTO users (username,password,role,email,name) VALUES (?,?,?,?,?)",
                  ("admin","admin123","admin","admin@hospital.com","Admin"))
        for i in range(1,4):
            c.execute("INSERT INTO users (username,password,role,email,name) VALUES (?,?,?,?,?)",
                (f"doctor{i}",f"doc{i}23","doctor",f"doctor{i}@hospital.com",f"Doctor {i}"))
        c.execute("INSERT INTO users (username,password,role,email,name) VALUES (?,?,?,?,?)",
                  ("patient1","pat123","patient","john@email.com","John Doe"))

        # Doctors
        doctors_data = [
            (2,"Dr. Ramesh Kumar","Cardiology","Heart Disease",12,"MD, DM Cardiology","9AM,11AM,2PM"),
            (3,"Dr. Priya Shah","Endocrinology","Diabetes",8,"MD, DNB","10AM,12PM,3PM"),
            (4,"Dr. Arjun Mehta","Nephrology","Kidney Disease",10,"MD, DM Nephrology","9AM,1PM,4PM"),
        ]
        c.executemany("INSERT INTO doctors (user_id,name,department,specialization,experience,qualification,available_slots) VALUES (?,?,?,?,?,?,?)", doctors_data)

        # Staff
        staff_data = [
            ("Nurse Ananya","nurse","Cardiology","Morning","9876543210","ananya@hospital.com","BSc Nursing",3,0,"Active"),
            ("Nurse Ravi","nurse","ICU","Night","9876543211","ravi@hospital.com","GNM",5,0,"Active"),
            ("Nurse Deepa","nurse","Pediatrics","Evening","9876543212","deepa@hospital.com","BSc Nursing",2,1,"On Leave"),
            ("Staff Mohan","support","Housekeeping","Morning","9876543213","mohan@hospital.com","",1,0,"Active"),
            ("Lab Tech Suresh","support","Lab","Morning","9876543214","suresh@hospital.com","DMLT",4,0,"Active"),
        ]
        c.executemany("INSERT INTO staff (name,role,department,shift,phone,email,qualification,experience,on_leave,status) VALUES (?,?,?,?,?,?,?,?,?,?)", staff_data)

        # Patient
        c.execute("INSERT INTO patients (user_id,name,age,gender,blood_group,phone,email) VALUES (?,?,?,?,?,?,?)",
                  (5,"John Doe",45,"Male","O+","9876500001","john@email.com"))

        # More demo patients
        more_patients = [
            ("Priya Patel",38,"Female","B+","9876500002","priya@email.com","Hypertension"),
            ("Rajesh Singh",55,"Male","A+","9876500003","rajesh@email.com","Diabetes Type 2"),
            ("Meera Nair",29,"Female","O-","9876500004","meera@email.com",""),
            ("Amit Sharma",62,"Male","AB+","9876500005","amit@email.com","Heart Disease"),
        ]
        for p in more_patients:
            c.execute("INSERT INTO patients (name,age,gender,blood_group,phone,email,medical_conditions) VALUES (?,?,?,?,?,?,?)", p)

        # Appointments (sample)
        from datetime import date, timedelta
        today = date.today().isoformat()
        tomorrow = (date.today()+timedelta(1)).isoformat()
        appts = [
            (1,1,today,"10:00 AM","Regular checkup","confirmed","Regular Checkup"),
            (2,2,today,"11:30 AM","Diabetes follow-up","pending","Follow-up"),
            (1,3,tomorrow,"2:00 PM","Kidney function test","pending","Lab Test"),
            (3,1,today,"12:00 PM","BP monitoring","confirmed","Regular Checkup"),
            (4,2,tomorrow,"3:00 PM","Insulin adjustment","pending","Follow-up"),
        ]
        c.executemany("INSERT INTO appointments (patient_id,doctor_id,appointment_date,time_slot,notes,status,type) VALUES (?,?,?,?,?,?,?)", appts)

        # Beds
        beds = []
        for i in range(1,61):  beds.append(("General Ward",f"GW-{i:03d}","General","available" if i%4!=0 else "occupied"))
        for i in range(1,21):  beds.append(("ICU Ward",    f"IC-{i:03d}","ICU",    "available" if i%3!=0 else "occupied"))
        for i in range(1,21):  beds.append(("Pediatric Ward",f"PD-{i:03d}","Pediatric","available" if i%5!=0 else "occupied"))
        for i in range(1,16):  beds.append(("Surgery Ward",f"SW-{i:03d}","Surgery","available" if i%6!=0 else "occupied"))
        c.executemany("INSERT INTO beds (ward,bed_number,bed_type,status) VALUES (?,?,?,?)", beds)

        # Resources
        resources = [
            ("Ventilator","Equipment",10,7),
            ("Oxygen Unit","Supply",50,38),
            ("ECG Machine","Equipment",8,6),
            ("MRI Scanner","Equipment",2,1),
            ("X-Ray Machine","Equipment",5,4),
            ("Wheelchair","Equipment",20,15),
        ]
        c.executemany("INSERT INTO resources (resource_name,resource_type,total,available) VALUES (?,?,?,?)", resources)

        # Welcome notification
        c.execute("INSERT INTO notifications (message,type) VALUES (?,?)",
                  ("System initialized. Welcome to MediCare AI!","success"))

    except Exception as e:
        print(f"Seed skipped (already exists): {e}")

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    # Delete old DB and recreate
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Old database removed.")
    init_database()