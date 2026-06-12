from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3, os

# ── Root directory — works both locally and on Render ─────────────────────────
# When running locally:  ROOT = healthcare_system/
# When running on Render: ROOT = /opt/render/project/src/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    static_folder=os.path.join(ROOT_DIR, 'frontend'),
    static_url_path=''
)
app.secret_key = os.environ.get('SECRET_KEY', 'healthcare_secret_2024')
CORS(app, supports_credentials=True)

DB_PATH = os.path.join(ROOT_DIR, 'database', 'healthcare.db')
ML_PATH = os.path.join(ROOT_DIR, 'ml_models', 'saved_models')
FRONT   = os.path.join(ROOT_DIR, 'frontend')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — so /staff, /beds, /appointments etc. work in the browser
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory(FRONT, 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory(FRONT, 'dashboard.html')

@app.route('/appointments')
def appointments_page():
    return send_from_directory(FRONT, 'appointments.html')

@app.route('/beds')
def beds_page():
    return send_from_directory(FRONT, 'beds.html')

@app.route('/staff')
def staff_page():
    return send_from_directory(FRONT, 'staff.html')

@app.route('/patients')
def patients_page():
    return send_from_directory(FRONT, 'patients.html')

@app.route('/predict')
def predict_page():
    return send_from_directory(FRONT, 'predict.html')

@app.route('/ehr')
def ehr_page():
    return send_from_directory(FRONT, 'ehr.html')

@app.route('/resources')
def resources_page():
    return send_from_directory(FRONT, 'resources.html')

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER — internal notification writer (no route, called by other routes)
# ═══════════════════════════════════════════════════════════════════════════════

def _add_notification(conn, message, ntype='info'):
    """Insert a notification row. Caller must commit."""
    conn.execute(
        "INSERT INTO notifications (message, type) VALUES (?, ?)",
        (message, ntype)
    )

def _recommend(disease, sev):
    r = {
        'diabetes': {
            'High':   'Immediate endocrinologist consult. Start glucose management.',
            'Medium': 'Monitor blood sugar weekly. Diet & exercise plan required.',
            'Low':    'Routine checkup in 6 months. Maintain healthy lifestyle.',
        },
        'heart': {
            'High':   'Urgent cardiology referral. ECG & stress test needed.',
            'Medium': 'Lipid profile test. Lifestyle modification required.',
            'Low':    'Annual cardiac checkup. Heart-healthy diet advised.',
        },
        'kidney': {
            'High':   'Immediate nephrology consult. Creatinine monitoring required.',
            'Medium': 'Renal diet. Regular urine and blood tests advised.',
            'Low':    'Stay hydrated. Routine checkup in 6 months.',
        },
        'outcome': {
            'High':   'ICU monitoring may be required. Close observation needed.',
            'Medium': 'Standard ward admission. Regular vitals monitoring.',
            'Low':    'Good recovery expected. Outpatient follow-up sufficient.',
        },
    }
    return r.get(disease, {}).get(sev, 'Consult a specialist.')

# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    if not d or not d.get('username') or not d.get('password'):
        return jsonify({"success": False, "message": "Username and password required"}), 400
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (d['username'],)
    ).fetchone()
    conn.close()
    if user and user['password'] == d['password']:
        session['user_id'] = user['id']
        session['role']    = user['role']
        return jsonify({
            "success":  True,
            "role":     user['role'],
            "user_id":  user['id'],
            "username": user['username'],
            "name":     user['name'],
        })
    return jsonify({"success": False, "message": "Invalid username or password"}), 401


@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    if not d or not d.get('username') or not d.get('password'):
        return jsonify({"success": False, "message": "Username and password required"}), 400
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password, role, email, name, phone) VALUES (?,?,?,?,?,?)",
            (
                d['username'],
                d['password'],
                d.get('role', 'patient'),
                d.get('email', ''),
                d.get('name', ''),
                d.get('phone', ''),
            )
        )
        uid = conn.execute(
            "SELECT id FROM users WHERE username = ?", (d['username'],)
        ).fetchone()['id']

        if d.get('role', 'patient') == 'patient':
            conn.execute(
                """INSERT INTO patients
                   (user_id, name, age, gender, blood_group, phone, email)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    uid,
                    d.get('name', ''),
                    d.get('age', 0),
                    d.get('gender', ''),
                    d.get('blood_group', ''),
                    d.get('phone', ''),
                    d.get('email', ''),
                )
            )

        _add_notification(
            conn,
            f"New user registered: {d.get('name', d['username'])} ({d.get('role','patient')})",
            'info'
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        conn.close()


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route('/api/session', methods=['GET'])
def get_session():
    if 'user_id' in session:
        conn = get_db()
        u = conn.execute(
            "SELECT * FROM users WHERE id = ?", (session['user_id'],)
        ).fetchone()
        conn.close()
        if u:
            return jsonify({
                "logged_in": True,
                "user_id":   u['id'],
                "username":  u['username'],
                "role":      u['role'],
                "name":      u['name'],
            })
    return jsonify({"logged_in": False})

# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/patients', methods=['GET', 'POST'])
def patients():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        if not d or not d.get('name'):
            conn.close()
            return jsonify({"success": False, "message": "Patient name required"}), 400
        try:
            conn.execute(
                """INSERT INTO patients
                   (user_id, name, age, gender, blood_group, phone, email,
                    medical_conditions, allergies, family_history, insurance)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    d.get('user_id'),
                    d['name'],
                    d.get('age', 0),
                    d.get('gender', ''),
                    d.get('blood_group', ''),
                    d.get('phone', ''),
                    d.get('email', ''),
                    d.get('medical_conditions', ''),
                    d.get('allergies', ''),
                    d.get('family_history', ''),
                    d.get('insurance', ''),
                )
            )
            conn.commit()
            _add_notification(conn, f"New patient registered: {d['name']}", 'success')
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
        finally:
            conn.close()

    # GET — return all patients
    rows = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/patients/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
def patient_detail(pid):
    conn = get_db()
    if request.method == 'PUT':
        d = request.json
        conn.execute(
            """UPDATE patients
               SET name=?, age=?, gender=?, blood_group=?, phone=?,
                   medical_conditions=?, allergies=?, family_history=?, insurance=?
               WHERE id=?""",
            (
                d.get('name', ''),
                d.get('age', 0),
                d.get('gender', ''),
                d.get('blood_group', ''),
                d.get('phone', ''),
                d.get('medical_conditions', ''),
                d.get('allergies', ''),
                d.get('family_history', ''),
                d.get('insurance', ''),
                pid,
            )
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        conn.execute("DELETE FROM patients WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # GET
    p = conn.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    conn.close()
    if p:
        return jsonify(dict(p))
    return jsonify({"error": "Not found"}), 404

# ═══════════════════════════════════════════════════════════════════════════════
# DOCTOR ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/doctors', methods=['GET', 'POST'])
def doctors():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        if not d or not d.get('name'):
            conn.close()
            return jsonify({"success": False, "message": "Doctor name required"}), 400
        try:
            # Create a login user account for the doctor
            username = d.get('username') or d['name'].lower().replace(' ', '_')
            password = d.get('password', 'doctor123')
            try:
                conn.execute(
                    "INSERT INTO users (username, password, role, email, name, phone) VALUES (?,?,?,?,?,?)",
                    (username, password, 'doctor', d.get('email', ''), d['name'], d.get('phone', ''))
                )
                uid = conn.execute(
                    "SELECT id FROM users WHERE username=?", (username,)
                ).fetchone()['id']
            except Exception:
                uid = None  # username might already exist

            conn.execute(
                """INSERT INTO doctors
                   (user_id, name, department, specialization, experience,
                    qualification, phone, email, status, available_slots)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    uid,
                    d['name'],
                    d.get('department', 'General'),
                    d.get('specialization', ''),
                    d.get('experience', 0),
                    d.get('qualification', ''),
                    d.get('phone', ''),
                    d.get('email', ''),
                    d.get('status', 'On Shift'),
                    d.get('available_slots', '9AM,11AM,2PM,4PM'),
                )
            )
            conn.commit()
            _add_notification(
                conn,
                f"New doctor added: {d['name']} — {d.get('department', 'General')}",
                'info'
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
        finally:
            conn.close()

    # GET
    rows = conn.execute("SELECT * FROM doctors ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/doctors/<int:did>', methods=['GET', 'PUT', 'DELETE'])
def doctor_detail(did):
    conn = get_db()
    if request.method == 'PUT':
        d = request.json
        conn.execute(
            """UPDATE doctors
               SET name=?, department=?, specialization=?, experience=?,
                   qualification=?, phone=?, email=?, status=?, available_slots=?
               WHERE id=?""",
            (
                d.get('name', ''),
                d.get('department', ''),
                d.get('specialization', ''),
                d.get('experience', 0),
                d.get('qualification', ''),
                d.get('phone', ''),
                d.get('email', ''),
                d.get('status', 'On Shift'),
                d.get('available_slots', '9AM,11AM,2PM,4PM'),
                did,
            )
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        conn.execute("DELETE FROM doctors WHERE id=?", (did,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # GET
    doc = conn.execute("SELECT * FROM doctors WHERE id=?", (did,)).fetchone()
    conn.close()
    if doc:
        return jsonify(dict(doc))
    return jsonify({"error": "Not found"}), 404

# ═══════════════════════════════════════════════════════════════════════════════
# STAFF (NURSES + SUPPORT) ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/staff-list', methods=['GET', 'POST'])
def staff_list():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        if not d or not d.get('name'):
            conn.close()
            return jsonify({"success": False, "message": "Staff name required"}), 400
        try:
            conn.execute(
                """INSERT INTO staff
                   (name, role, department, shift, phone, email,
                    qualification, experience, on_leave, status)
                   VALUES (?,?,?,?,?,?,?,?,0,'Active')""",
                (
                    d['name'],
                    d.get('role', 'nurse'),
                    d.get('department', 'General'),
                    d.get('shift', 'Morning'),
                    d.get('phone', ''),
                    d.get('email', ''),
                    d.get('qualification', ''),
                    d.get('experience', 0),
                )
            )
            conn.commit()
            _add_notification(
                conn,
                f"New staff added: {d['name']} ({d.get('role', 'nurse')}) — {d.get('department','')}",
                'info'
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
        finally:
            conn.close()

    # GET
    rows = conn.execute("SELECT * FROM staff ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/staff-list/<int:sid>', methods=['GET', 'PUT', 'DELETE'])
def staff_detail(sid):
    conn = get_db()
    if request.method == 'PUT':
        d = request.json
        conn.execute(
            """UPDATE staff
               SET name=?, department=?, shift=?, phone=?, status=?, on_leave=?
               WHERE id=?""",
            (
                d.get('name', ''),
                d.get('department', ''),
                d.get('shift', 'Morning'),
                d.get('phone', ''),
                d.get('status', 'Active'),
                d.get('on_leave', 0),
                sid,
            )
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        conn.execute("DELETE FROM staff WHERE id=?", (sid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # GET
    s = conn.execute("SELECT * FROM staff WHERE id=?", (sid,)).fetchone()
    conn.close()
    if s:
        return jsonify(dict(s))
    return jsonify({"error": "Not found"}), 404

# ═══════════════════════════════════════════════════════════════════════════════
# APPOINTMENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/appointments', methods=['GET', 'POST'])
def appointments_api():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        if not d or not d.get('patient_id') or not d.get('doctor_id') or not d.get('date'):
            conn.close()
            return jsonify({"success": False, "message": "patient_id, doctor_id and date are required"}), 400
        try:
            conn.execute(
                """INSERT INTO appointments
                   (patient_id, doctor_id, appointment_date, time_slot,
                    notes, status, type)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    d['patient_id'],
                    d['doctor_id'],
                    d['date'],
                    d.get('slot', '9AM'),
                    d.get('notes', ''),
                    d.get('status', 'pending'),
                    d.get('type', 'Regular Checkup'),
                )
            )
            conn.commit()

            # Build a friendly notification message
            pat = conn.execute(
                "SELECT name FROM patients WHERE id=?", (d['patient_id'],)
            ).fetchone()
            doc = conn.execute(
                "SELECT name FROM doctors WHERE id=?", (d['doctor_id'],)
            ).fetchone()
            pname = pat['name'] if pat else f"Patient #{d['patient_id']}"
            dname = doc['name'] if doc else f"Doctor #{d['doctor_id']}"
            _add_notification(
                conn,
                f"Appointment booked: {pname} with {dname} on {d['date']} at {d.get('slot','—')}",
                'success'
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
        finally:
            conn.close()

    # GET — join with patients and doctors for display names
    rows = conn.execute(
        """SELECT a.*,
                  p.name  AS patient_name,
                  doc.name AS doctor_name,
                  doc.department
           FROM appointments a
           LEFT JOIN patients p   ON a.patient_id = p.id
           LEFT JOIN doctors  doc ON a.doctor_id  = doc.id
           ORDER BY a.appointment_date DESC, a.id DESC"""
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/appointments/<int:aid>', methods=['GET', 'PUT', 'DELETE'])
def appointment_detail(aid):
    conn = get_db()
    if request.method == 'PUT':
        d = request.json
        conn.execute(
            "UPDATE appointments SET status=? WHERE id=?",
            (d.get('status', 'pending'), aid)
        )
        conn.commit()
        a = conn.execute(
            """SELECT a.*, p.name AS pname
               FROM appointments a
               LEFT JOIN patients p ON a.patient_id = p.id
               WHERE a.id=?""",
            (aid,)
        ).fetchone()
        if a:
            _add_notification(
                conn,
                f"Appointment #{aid} ({a['pname']}) status changed to {d.get('status','')}",
                'info'
            )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        conn.execute("DELETE FROM appointments WHERE id=?", (aid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # GET
    a = conn.execute(
        """SELECT a.*, p.name AS patient_name, doc.name AS doctor_name
           FROM appointments a
           LEFT JOIN patients p   ON a.patient_id = p.id
           LEFT JOIN doctors  doc ON a.doctor_id  = doc.id
           WHERE a.id=?""",
        (aid,)
    ).fetchone()
    conn.close()
    if a:
        return jsonify(dict(a))
    return jsonify({"error": "Not found"}), 404

# ═══════════════════════════════════════════════════════════════════════════════
# BED ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/beds', methods=['GET', 'POST'])
def beds_api():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        if not d or not d.get('ward') or not d.get('bed_number'):
            conn.close()
            return jsonify({"success": False, "message": "ward and bed_number required"}), 400
        try:
            conn.execute(
                "INSERT INTO beds (ward, bed_number, bed_type, status) VALUES (?,?,?,?)",
                (d['ward'], d['bed_number'], d.get('bed_type', d['ward']), 'available')
            )
            conn.commit()
            conn.close()
            return jsonify({"success": True})
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({"success": False, "message": str(e)}), 400

    # GET
    rows = conn.execute(
        "SELECT * FROM beds ORDER BY ward, bed_number"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/beds/<int:bid>', methods=['GET', 'PUT'])
def bed_detail(bid):
    conn = get_db()
    if request.method == 'PUT':
        d = request.json
        conn.execute(
            "UPDATE beds SET status=?, patient_id=? WHERE id=?",
            (d.get('status', 'available'), d.get('patient_id'), bid)
        )
        conn.commit()
        _add_notification(
            conn,
            f"Bed #{bid} status updated to {d.get('status','—')}",
            'info'
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # GET
    b = conn.execute("SELECT * FROM beds WHERE id=?", (bid,)).fetchone()
    conn.close()
    if b:
        return jsonify(dict(b))
    return jsonify({"error": "Not found"}), 404

# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/resources', methods=['GET', 'POST'])
def resources_api():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute(
            """INSERT INTO resources (resource_name, resource_type, total, available)
               VALUES (?,?,?,?)""",
            (d['resource_name'], d.get('resource_type', 'Equipment'),
             d.get('total', 0), d.get('available', 0))
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    rows = conn.execute("SELECT * FROM resources ORDER BY resource_name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/resources/<int:rid>', methods=['PUT'])
def resource_detail(rid):
    d = request.json
    conn = get_db()
    conn.execute(
        "UPDATE resources SET available=?, total=? WHERE id=?",
        (d.get('available', 0), d.get('total', 0), rid)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ═══════════════════════════════════════════════════════════════════════════════
# EHR ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/ehr', methods=['GET', 'POST'])
def ehr_api():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        if not d or not d.get('patient_id') or not d.get('date'):
            conn.close()
            return jsonify({"success": False, "message": "patient_id and date required"}), 400
        try:
            conn.execute(
                """INSERT INTO ehr
                   (patient_id, diagnosis, prescription, treatment_history,
                    visit_date, doctor_id, lab_reports)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    d['patient_id'],
                    d.get('diagnosis', ''),
                    d.get('prescription', ''),
                    d.get('treatment', ''),
                    d['date'],
                    d.get('doctor_id', 1),
                    d.get('lab_reports', ''),
                )
            )
            conn.commit()
            pat = conn.execute(
                "SELECT name FROM patients WHERE id=?", (d['patient_id'],)
            ).fetchone()
            pname = pat['name'] if pat else f"Patient #{d['patient_id']}"
            _add_notification(
                conn,
                f"EHR updated for {pname}: {d.get('diagnosis', '—')}",
                'success'
            )
            conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
        finally:
            conn.close()

    # GET — join with patient and doctor names
    rows = conn.execute(
        """SELECT e.*,
                  p.name   AS patient_name,
                  doc.name AS doctor_name
           FROM ehr e
           LEFT JOIN patients p   ON e.patient_id = p.id
           LEFT JOIN doctors  doc ON e.doctor_id  = doc.id
           ORDER BY e.visit_date DESC"""
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/ehr/<int:eid>', methods=['GET', 'PUT', 'DELETE'])
def ehr_detail(eid):
    conn = get_db()
    if request.method == 'PUT':
        d = request.json
        conn.execute(
            """UPDATE ehr
               SET diagnosis=?, prescription=?, treatment_history=?,
                   lab_reports=?, visit_date=?
               WHERE id=?""",
            (
                d.get('diagnosis', ''),
                d.get('prescription', ''),
                d.get('treatment', ''),
                d.get('lab_reports', ''),
                d.get('date', ''),
                eid,
            )
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    if request.method == 'DELETE':
        conn.execute("DELETE FROM ehr WHERE id=?", (eid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

    # GET
    e = conn.execute("SELECT * FROM ehr WHERE id=?", (eid,)).fetchone()
    conn.close()
    if e:
        return jsonify(dict(e))
    return jsonify({"error": "Not found"}), 404

# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/notifications/unread-count', methods=['GET'])
def unread_count():
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE is_read = 0"
    ).fetchone()[0]
    conn.close()
    return jsonify({"count": count})


@app.route('/api/notifications/read', methods=['POST'])
def mark_all_read():
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1")
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route('/api/notifications/<int:nid>/read', methods=['PUT'])
def mark_one_read(nid):
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (nid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route('/api/notifications/<int:nid>', methods=['DELETE'])
def delete_notification(nid):
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE id = ?", (nid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ═══════════════════════════════════════════════════════════════════════════════
# ML PREDICTION ROUTE
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        import joblib
        import numpy as np
    except ImportError:
        return jsonify({"error": "joblib / numpy not installed"}), 500

    d = request.json
    if not d:
        return jsonify({"error": "No data provided"}), 400

    disease = d.get('disease_type', 'diabetes')

    model_map = {
        'diabetes': (
            'diabetes_model.pkl',
            ['age', 'bmi', 'glucose', 'blood_pressure', 'insulin', 'cholesterol']
        ),
        'heart': (
            'heart_model.pkl',
            ['age', 'cholesterol', 'blood_pressure', 'bmi', 'smoking', 'diabetes']
        ),
        'kidney': (
            'kidney_model.pkl',
            ['age', 'blood_pressure', 'glucose', 'blood_urea', 'creatinine', 'hemoglobin']
        ),
        'outcome': (
            'outcome_model.pkl',
            ['age', 'severity', 'comorbidities', 'bmi', 'blood_pressure']
        ),
    }

    if disease not in model_map:
        return jsonify({"error": f"Unknown disease type: {disease}"}), 400

    fname, features = model_map[disease]
    model_path = os.path.join(ML_PATH, fname)

    if not os.path.exists(model_path):
        return jsonify({
            "error": f"Model file not found: {fname}. Run: python ml_models/train_models.py"
        }), 500

    try:
        model  = joblib.load(model_path)
        values = np.array([[float(d.get(f, 0)) for f in features]])
        prob   = model.predict_proba(values)[0][1]
        pred   = int(model.predict(values)[0])
        sev    = "High" if prob > 0.7 else "Medium" if prob > 0.4 else "Low"

        disease_labels = {
            'diabetes': 'Diabetes',
            'heart':    'Heart Disease',
            'kidney':   'Kidney Disease',
            'outcome':  'Recovery Prediction',
        }
        dname = disease_labels[disease]
        score = round(prob * 100, 1)

        # Persist prediction + fire notification if a patient_id was passed
        if d.get('patient_id'):
            conn = get_db()
            conn.execute(
                """INSERT INTO predictions
                   (patient_id, disease_type, risk_score, predicted_disease, severity)
                   VALUES (?,?,?,?,?)""",
                (d['patient_id'], disease, score, dname, sev)
            )
            notif_type = 'warning' if sev == 'High' else 'info'
            _add_notification(
                conn,
                f"AI prediction: {dname} risk {sev} ({score}%) for patient #{d['patient_id']}",
                notif_type
            )
            conn.commit()
            conn.close()

        return jsonify({
            "risk_score":      score,
            "prediction":      pred,
            "severity":        sev,
            "disease":         dname,
            "recommendation":  _recommend(disease, sev),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    conn = get_db()
    rows = conn.execute(
        """SELECT pr.*, p.name AS patient_name
           FROM predictions pr
           LEFT JOIN patients p ON pr.patient_id = p.id
           ORDER BY pr.created_at DESC
           LIMIT 50"""
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ═══════════════════════════════════════════════════════════════════════════════
# STATS / DASHBOARD ROUTE
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/stats', methods=['GET'])
def stats():
    from datetime import date
    conn   = get_db()
    today  = date.today().isoformat()

    data = {
        # counts
        "patients":        conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
        "doctors":         conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
        "nurses":          conn.execute("SELECT COUNT(*) FROM staff WHERE role='nurse'").fetchone()[0],
        "support_staff":   conn.execute("SELECT COUNT(*) FROM staff WHERE role='support'").fetchone()[0],
        "on_leave":        conn.execute("SELECT COUNT(*) FROM staff WHERE on_leave=1").fetchone()[0],

        # beds
        "total_beds":      conn.execute("SELECT COUNT(*) FROM beds").fetchone()[0],
        "available_beds":  conn.execute("SELECT COUNT(*) FROM beds WHERE status='available'").fetchone()[0],
        "occupied_beds":   conn.execute("SELECT COUNT(*) FROM beds WHERE status='occupied'").fetchone()[0],

        # appointments
        "today_appts":     conn.execute(
                               "SELECT COUNT(*) FROM appointments WHERE appointment_date=?",
                               (today,)
                           ).fetchone()[0],
        "pending_appts":   conn.execute(
                               "SELECT COUNT(*) FROM appointments WHERE status='pending'"
                           ).fetchone()[0],
        "confirmed_appts": conn.execute(
                               "SELECT COUNT(*) FROM appointments WHERE status='confirmed'"
                           ).fetchone()[0],
        "cancelled_appts": conn.execute(
                               "SELECT COUNT(*) FROM appointments WHERE status='cancelled'"
                           ).fetchone()[0],

        # ai
        "predictions":     conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],

        # notifications
        "unread_notifs":   conn.execute(
                               "SELECT COUNT(*) FROM notifications WHERE is_read=0"
                           ).fetchone()[0],
    }

    # Per-ward breakdown
    for ward in ['General Ward', 'ICU Ward', 'Pediatric Ward', 'Surgery Ward']:
        key    = ward.lower().replace(' ward', '').replace(' ', '_')
        total  = conn.execute(
            "SELECT COUNT(*) FROM beds WHERE ward=?", (ward,)
        ).fetchone()[0]
        occup  = conn.execute(
            "SELECT COUNT(*) FROM beds WHERE ward=? AND status='occupied'", (ward,)
        ).fetchone()[0]
        data[f"{key}_total"]    = total
        data[f"{key}_occupied"] = occup
        data[f"{key}_available"]= total - occup

    conn.close()
    return jsonify(data)

# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH ROUTE — global search across patients, doctors, appointments
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/search', methods=['GET'])
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"patients": [], "doctors": [], "appointments": []})

    like = f"%{q}%"
    conn = get_db()

    patients = conn.execute(
        "SELECT id, name, age, gender, blood_group FROM patients WHERE name LIKE ? LIMIT 5",
        (like,)
    ).fetchall()

    doctors = conn.execute(
        "SELECT id, name, department, specialization FROM doctors WHERE name LIKE ? OR department LIKE ? LIMIT 5",
        (like, like)
    ).fetchall()

    appointments = conn.execute(
        """SELECT a.id, p.name AS patient_name, doc.name AS doctor_name,
                  a.appointment_date, a.status
           FROM appointments a
           LEFT JOIN patients p   ON a.patient_id = p.id
           LEFT JOIN doctors  doc ON a.doctor_id  = doc.id
           WHERE p.name LIKE ? OR doc.name LIKE ?
           LIMIT 5""",
        (like, like)
    ).fetchall()

    conn.close()
    return jsonify({
        "patients":     [dict(r) for r in patients],
        "doctors":      [dict(r) for r in doctors],
        "appointments": [dict(r) for r in appointments],
    })

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════



    # ═══════════════════════════════════════════════════════════════════════════════
# PDF REPORT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from flask import send_file
from datetime import datetime

# ── colour palette ────────────────────────────────────────────────────────────
PURPLE  = colors.HexColor('#7C6FD4')
MINT    = colors.HexColor('#4CAF8A')
PINK    = colors.HexColor('#E8698A')
SKY     = colors.HexColor('#5B9BD5')
PEACH   = colors.HexColor('#E8965A')
LAVENDER= colors.HexColor('#9B8DE8')
DARK    = colors.HexColor('#3D3066')
MUTED   = colors.HexColor('#7B6FA0')
LIGHT1  = colors.HexColor('#F0EBFF')
LIGHT2  = colors.HexColor('#E8F8F0')
WHITE   = colors.white
BG_GRAY = colors.HexColor('#F8F4FF')

def _pdf_header(elements, styles, title, subtitle=''):
    """Reusable pastel header block for all PDF reports."""
    # Top colour strip
    header_data = [[Paragraph(
        f'<font color="#FFFFFF" size="18"><b>🏥 HealthAI</b></font> '
        f'<font color="#E0D8FF" size="11"> — Smart Healthcare System</font>',
        ParagraphStyle('hdr', fontName='Helvetica-Bold',
                       fontSize=18, textColor=WHITE)
    )]]
    header_tbl = Table(header_data, colWidths=[17*cm])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PURPLE),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING',   (0,0), (-1,-1), 20),
        ('ROUNDEDCORNERS', [8, 8, 0, 0]),
    ]))
    elements.append(header_tbl)

    # Title row
    title_data = [[
        Paragraph(f'<b>{title}</b>',
                  ParagraphStyle('t2', fontName='Helvetica-Bold',
                                 fontSize=16, textColor=DARK)),
        Paragraph(
            f'<font color="#7B6FA0" size="9">Generated: '
            f'{datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
            ParagraphStyle('date', fontName='Helvetica',
                           fontSize=9, textColor=MUTED, alignment=TA_RIGHT)
        )
    ]]
    title_tbl = Table(title_data, colWidths=[11*cm, 6*cm])
    title_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), LIGHT1),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(title_tbl)

    if subtitle:
        sub_data = [[Paragraph(
            f'<font color="#7B6FA0" size="9">{subtitle}</font>',
            ParagraphStyle('sub', fontName='Helvetica',
                           fontSize=9, textColor=MUTED)
        )]]
        sub_tbl = Table(sub_data, colWidths=[17*cm])
        sub_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), LIGHT2),
            ('TOPPADDING',    (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ]))
        elements.append(sub_tbl)

    elements.append(Spacer(1, 14))


def _styled_table(data, col_widths, header_bg=PURPLE):
    """Build a nicely styled reportlab Table."""
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        # Header row
        ('BACKGROUND',    (0,0), (-1,0),  header_bg),
        ('TEXTCOLOR',     (0,0), (-1,0),  WHITE),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  9),
        ('TOPPADDING',    (0,0), (-1,0),  9),
        ('BOTTOMPADDING', (0,0), (-1,0),  9),
        # Data rows
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 8),
        ('TOPPADDING',    (0,1), (-1,-1), 7),
        ('BOTTOMPADDING', (0,1), (-1,-1), 7),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, LIGHT1]),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#E8E0F5')),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl


def _summary_box(elements, items, bg=LIGHT1):
    """Two-column summary/info box."""
    rows = []
    pairs = list(items.items())
    for i in range(0, len(pairs), 2):
        left  = pairs[i]
        right = pairs[i+1] if i+1 < len(pairs) else ('', '')
        rows.append([
            Paragraph(f'<b><font color="#7C6FD4">{left[0]}:</font></b>',
                      ParagraphStyle('k', fontName='Helvetica-Bold',
                                     fontSize=8, textColor=PURPLE)),
            Paragraph(f'<font size="8">{left[1]}</font>',
                      ParagraphStyle('v', fontName='Helvetica', fontSize=8)),
            Paragraph(f'<b><font color="#7C6FD4">{right[0]}:</font></b>',
                      ParagraphStyle('k2', fontName='Helvetica-Bold',
                                     fontSize=8, textColor=PURPLE)),
            Paragraph(f'<font size="8">{right[1]}</font>',
                      ParagraphStyle('v2', fontName='Helvetica', fontSize=8)),
        ])
    box = Table(rows, colWidths=[4*cm, 4.5*cm, 4*cm, 4.5*cm])
    box.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), bg),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#E8E0F5')),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(box)
    elements.append(Spacer(1, 10))


# ── APPOINTMENT PDF ───────────────────────────────────────────────────────────
@app.route('/api/reports/appointments')
def report_appointments():
    conn = get_db()
    rows = conn.execute("""
        SELECT a.id, p.name AS patient, doc.name AS doctor,
               doc.department, a.appointment_date, a.time_slot,
               a.type, a.status, a.notes
        FROM appointments a
        LEFT JOIN patients p   ON a.patient_id = p.id
        LEFT JOIN doctors  doc ON a.doctor_id  = doc.id
        ORDER BY a.appointment_date DESC
    """).fetchall()

    total     = len(rows)
    confirmed = sum(1 for r in rows if r['status'] == 'confirmed')
    pending   = sum(1 for r in rows if r['status'] == 'pending')
    cancelled = sum(1 for r in rows if r['status'] == 'cancelled')
    conn.close()

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elems  = []

    _pdf_header(elems, styles,
                '📅 Appointment Report',
                f'Complete appointment records — {datetime.now().strftime("%d %B %Y")}')

    # Summary
    _summary_box(elems, {
        'Total Appointments': str(total),
        'Confirmed':          str(confirmed),
        'Pending':            str(pending),
        'Cancelled':          str(cancelled),
    }, LIGHT1)

    # Status legend
    legend = [[
        Paragraph('<b>Status Legend:</b>', ParagraphStyle('lg', fontSize=8, textColor=DARK)),
        Paragraph('<font color="#2d9e6a">● Confirmed</font>',
                  ParagraphStyle('l1', fontSize=8)),
        Paragraph('<font color="#e6a817">● Pending</font>',
                  ParagraphStyle('l2', fontSize=8)),
        Paragraph('<font color="#e74c3c">● Cancelled</font>',
                  ParagraphStyle('l3', fontSize=8)),
    ]]
    leg_tbl = Table(legend, colWidths=[4*cm, 4*cm, 4*cm, 5*cm])
    leg_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), LIGHT2),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
    ]))
    elems.append(leg_tbl)
    elems.append(Spacer(1, 10))

    # Table
    def status_color(s):
        return ({'confirmed':'#2d9e6a','pending':'#e6a817','cancelled':'#e74c3c'}
                .get(s, '#666666'))

    header = ['#', 'Patient', 'Doctor', 'Department',
              'Date', 'Time', 'Type', 'Status', 'Notes']
    data   = [header]
    for r in rows:
        sc = status_color(r['status'])
        data.append([
            str(r['id']),
            r['patient']  or '—',
            r['doctor']   or '—',
            r['department'] or '—',
            r['appointment_date'] or '—',
            r['time_slot'] or '—',
            r['type']     or '—',
            Paragraph(f'<font color="{sc}"><b>{r["status"].upper()}</b></font>',
                      ParagraphStyle('s', fontSize=7)),
            (r['notes'] or '—')[:30],
        ])

    elems.append(_styled_table(
        data,
        [1*cm, 3*cm, 3*cm, 2.8*cm,
         2.4*cm, 1.6*cm, 2.5*cm, 2*cm, 2.7*cm]
    ))
    elems.append(Spacer(1, 16))

    # Footer
    elems.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E8E0F5')))
    elems.append(Paragraph(
        '<font color="#7B6FA0" size="8">HealthAI — Smart Healthcare System | '
        'Confidential Medical Document | '
        f'Generated on {datetime.now().strftime("%d %b %Y at %I:%M %p")}</font>',
        ParagraphStyle('foot', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'appointments_{datetime.now().strftime("%Y%m%d")}.pdf',
                     mimetype='application/pdf')


# ── EHR PDF ───────────────────────────────────────────────────────────────────
@app.route('/api/reports/ehr')
def report_ehr():
    conn = get_db()
    records = conn.execute("""
        SELECT e.id, p.name AS patient, p.age, p.blood_group,
               doc.name AS doctor, doc.department,
               e.diagnosis, e.prescription, e.treatment_history,
               e.lab_reports, e.visit_date
        FROM ehr e
        LEFT JOIN patients p   ON e.patient_id = p.id
        LEFT JOIN doctors  doc ON e.doctor_id  = doc.id
        ORDER BY e.visit_date DESC
    """).fetchall()
    conn.close()

    buf   = io.BytesIO()
    doc   = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=1.5*cm, rightMargin=1.5*cm,
                              topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles= getSampleStyleSheet()
    elems = []

    _pdf_header(elems, styles,
                '📋 Electronic Health Records (EHR)',
                'Complete patient medical history and treatment records')

    _summary_box(elems, {
        'Total Records':   str(len(records)),
        'Report Date':     datetime.now().strftime('%d %b %Y'),
        'System':          'HealthAI EHR Module',
        'Classification':  'Confidential',
    }, LIGHT2)

    if not records:
        elems.append(Paragraph('No EHR records found.',
                                ParagraphStyle('empty', fontSize=10,
                                               textColor=MUTED, alignment=TA_CENTER)))
    else:
        for rec in records:
            # Per-record card
            card_header = [[Paragraph(
                f'<b><font color="white">Patient: {rec["patient"] or "Unknown"} '
                f'| Visit: {rec["visit_date"] or "—"} '
                f'| Doctor: {rec["doctor"] or "—"} ({rec["department"] or "—"})</font></b>',
                ParagraphStyle('ch', fontName='Helvetica-Bold',
                               fontSize=9, textColor=WHITE)
            )]]
            ch_tbl = Table(card_header, colWidths=[17*cm])
            ch_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), LAVENDER),
                ('TOPPADDING',    (0,0), (-1,-1), 7),
                ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                ('LEFTPADDING',   (0,0), (-1,-1), 12),
            ]))
            elems.append(ch_tbl)

            # Detail rows
            detail_rows = [
                ['Age / Blood Group',
                 f'{rec["age"] or "—"} yrs / {rec["blood_group"] or "—"}',
                 'Record ID', f'EHR-{str(rec["id"]).zfill(4)}'],
                ['Diagnosis',
                 (rec['diagnosis'] or '—')[:80],
                 'Lab Reports',
                 (rec['lab_reports'] or '—')[:40]],
                ['Prescription',
                 (rec['prescription'] or '—')[:80],
                 'Treatment',
                 (rec['treatment_history'] or '—')[:40]],
            ]
            det_rows_formatted = []
            for row in detail_rows:
                det_rows_formatted.append([
                    Paragraph(f'<b><font color="#7C6FD4">{row[0]}</font></b>',
                              ParagraphStyle('dk', fontName='Helvetica-Bold',
                                             fontSize=8, textColor=PURPLE)),
                    Paragraph(f'<font size="8">{row[1]}</font>',
                              ParagraphStyle('dv', fontSize=8)),
                    Paragraph(f'<b><font color="#7C6FD4">{row[2]}</font></b>',
                              ParagraphStyle('dk2', fontName='Helvetica-Bold',
                                             fontSize=8, textColor=PURPLE)),
                    Paragraph(f'<font size="8">{row[3]}</font>',
                              ParagraphStyle('dv2', fontSize=8)),
                ])
            det_tbl = Table(det_rows_formatted,
                            colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
            det_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), LIGHT1),
                ('ROWBACKGROUNDS',(0,0), (-1,-1), [WHITE, LIGHT1]),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 10),
                ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#E8E0F5')),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elems.append(det_tbl)
            elems.append(Spacer(1, 10))

    elems.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E8E0F5')))
    elems.append(Paragraph(
        f'<font color="#7B6FA0" size="8">HealthAI EHR Report | Confidential | '
        f'Generated {datetime.now().strftime("%d %b %Y at %I:%M %p")}</font>',
        ParagraphStyle('foot', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'ehr_records_{datetime.now().strftime("%Y%m%d")}.pdf',
                     mimetype='application/pdf')


# ── DISEASE PREDICTION PDF ────────────────────────────────────────────────────
@app.route('/api/reports/predictions')
def report_predictions():
    conn = get_db()
    preds = conn.execute("""
        SELECT pr.id, p.name AS patient, p.age, p.blood_group,
               pr.disease_type, pr.predicted_disease,
               pr.risk_score, pr.severity, pr.created_at
        FROM predictions pr
        LEFT JOIN patients p ON pr.patient_id = p.id
        ORDER BY pr.created_at DESC
    """).fetchall()
    conn.close()

    total  = len(preds)
    high   = sum(1 for p in preds if p['severity'] == 'High')
    medium = sum(1 for p in preds if p['severity'] == 'Medium')
    low    = sum(1 for p in preds if p['severity'] == 'Low')

    buf   = io.BytesIO()
    doc   = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=1.5*cm, rightMargin=1.5*cm,
                              topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles= getSampleStyleSheet()
    elems = []

    _pdf_header(elems, styles,
                '🧠 AI Disease Prediction Report',
                'ML-powered disease risk analysis results')

    _summary_box(elems, {
        'Total Predictions': str(total),
        'High Risk':         str(high),
        'Medium Risk':       str(medium),
        'Low Risk':          str(low),
    }, LIGHT1)

    # Risk bar graphic (text-based)
    if total:
        bar_data = [[
            Paragraph('<b>Risk Distribution:</b>',
                      ParagraphStyle('rb', fontSize=8, textColor=DARK)),
            Paragraph(
                f'<font color="#e74c3c">■■■ High: {high} ({round(high/total*100)}%)</font>  '
                f'<font color="#e6a817">■■■ Medium: {medium} ({round(medium/total*100)}%)</font>  '
                f'<font color="#2d9e6a">■■■ Low: {low} ({round(low/total*100)}%)</font>',
                ParagraphStyle('rb2', fontSize=8)),
        ]]
        bar_tbl = Table(bar_data, colWidths=[4*cm, 13*cm])
        bar_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), LIGHT2),
            ('TOPPADDING',    (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING',   (0,0), (-1,-1), 10),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elems.append(bar_tbl)
        elems.append(Spacer(1, 10))

    # Table
    def sev_color(s):
        return {'High':'#e74c3c','Medium':'#e6a817','Low':'#2d9e6a'}.get(s,'#666')

    def risk_bar(score):
        filled = int(score / 10)
        empty  = 10 - filled
        return f'{"█" * filled}{"░" * empty} {score}%'

    header = ['#','Patient','Age','Disease','Risk Score','Severity','Date']
    data   = [header]
    for p in preds:
        sc = sev_color(p['severity'])
        data.append([
            f'P-{str(p["id"]).zfill(3)}',
            p['patient'] or '—',
            str(p['age'] or '—'),
            p['predicted_disease'],
            Paragraph(f'<font face="Courier" size="8">{risk_bar(p["risk_score"])}</font>',
                      ParagraphStyle('rb3', fontSize=7)),
            Paragraph(f'<font color="{sc}"><b>{p["severity"]}</b></font>',
                      ParagraphStyle('sv', fontSize=8)),
            (p['created_at'] or '—')[:10],
        ])

    elems.append(_styled_table(
        data,
        [1.5*cm, 3.5*cm, 1.5*cm, 3.5*cm, 4*cm, 2*cm, 2*cm],
        header_bg=LAVENDER
    ))
    elems.append(Spacer(1, 16))

    # Individual detail cards for High-risk patients
    high_preds = [p for p in preds if p['severity'] == 'High']
    if high_preds:
        elems.append(Paragraph(
            '<b>🔴 High-Risk Patient Details</b>',
            ParagraphStyle('hrt', fontName='Helvetica-Bold',
                           fontSize=11, textColor=PINK)
        ))
        elems.append(Spacer(1, 8))
        for p in high_preds[:10]:   # cap at 10
            card = [[Paragraph(
                f'<b><font color="white">⚠ {p["patient"] or "Unknown"} — '
                f'{p["predicted_disease"]} — Risk: {p["risk_score"]}%</font></b>',
                ParagraphStyle('hc', fontName='Helvetica-Bold',
                               fontSize=9, textColor=WHITE)
            )]]
            c_tbl = Table(card, colWidths=[17*cm])
            c_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), PINK),
                ('TOPPADDING',    (0,0), (-1,-1), 7),
                ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                ('LEFTPADDING',   (0,0), (-1,-1), 12),
            ]))
            elems.append(c_tbl)
            _summary_box(elems, {
                'Age':        str(p['age'] or '—'),
                'Blood Group':p['blood_group'] or '—',
                'Disease':    p['predicted_disease'],
                'Detected':   (p['created_at'] or '—')[:10],
            }, colors.HexColor('#FFF0F3'))

    elems.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E8E0F5')))
    elems.append(Paragraph(
        f'<font color="#7B6FA0" size="8">HealthAI AI Prediction Report | Confidential | '
        f'Generated {datetime.now().strftime("%d %b %Y at %I:%M %p")}</font>',
        ParagraphStyle('foot', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'predictions_{datetime.now().strftime("%Y%m%d")}.pdf',
                     mimetype='application/pdf')


# ── DOCTOR PAGE ROUTE ─────────────────────────────────────────────────────────
@app.route('/doctor-login')
def doctor_login_page():
    return send_from_directory(FRONT, 'doctor_login.html')

@app.route('/doctor-dashboard')
def doctor_dashboard_page():
    return send_from_directory(FRONT, 'doctor_dashboard.html')
# ═══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL PATIENT PDF REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/reports/patient/<int:pid>/appointment/<int:aid>')
def report_single_appointment(pid, aid):
    """PDF for one specific appointment."""
    conn = get_db()
    appt = conn.execute("""
        SELECT a.*, p.name AS patient_name, p.age, p.gender, p.blood_group,
               p.phone AS patient_phone, p.email AS patient_email,
               p.medical_conditions, p.allergies,
               doc.name AS doctor_name, doc.department,
               doc.specialization, doc.qualification, doc.experience,
               doc.phone AS doctor_phone
        FROM appointments a
        LEFT JOIN patients p   ON a.patient_id = p.id
        LEFT JOIN doctors  doc ON a.doctor_id  = doc.id
        WHERE a.id = ? AND a.patient_id = ?
    """, (aid, pid)).fetchone()

    if not appt:
        conn.close()
        return jsonify({"error": "Appointment not found"}), 404

    # Get EHR records for this patient from same visit date
    ehr = conn.execute("""
        SELECT * FROM ehr
        WHERE patient_id = ? AND visit_date = ?
        ORDER BY id DESC LIMIT 1
    """, (pid, appt['appointment_date'])).fetchone()

    conn.close()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elems = []
    styles = getSampleStyleSheet()

    # ── Header ────────────────────────────────────────────────────────────────
    _pdf_header(elems, styles,
                f'📅 Appointment Report',
                f'Appointment ID: APT-{str(aid).zfill(4)} | '
                f'Patient: {appt["patient_name"]} | '
                f'Date: {appt["appointment_date"]}')

    # ── Status badge ──────────────────────────────────────────────────────────
    smap  = {'confirmed': ('#e8fff4','#2d9e6a','CONFIRMED ✓'),
             'pending':   ('#fff8e0','#e6a817','PENDING ⏳'),
             'cancelled': ('#ffe8e8','#e74c3c','CANCELLED ✗'),
             'completed': ('#e8f4ff','#5B9BD5','COMPLETED ✓')}
    sbg, sclr, slbl = smap.get(appt['status'],
                                ('#f0ebff','#7C6FD4', appt['status'].upper()))
    status_row = [[Paragraph(
        f'<b><font color="{sclr}" size="13">{slbl}</font></b>',
        ParagraphStyle('st', alignment=TA_CENTER,
                       fontName='Helvetica-Bold', fontSize=13)
    )]]
    st_tbl = Table(status_row, colWidths=[17*cm])
    st_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor(sbg)),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ROUNDEDCORNERS', [8,8,8,8]),
    ]))
    elems.append(st_tbl)
    elems.append(Spacer(1, 14))

    # ── Patient info card ────────────────────────────────────────────────────
    elems.append(Paragraph(
        '<b>👤 Patient Information</b>',
        ParagraphStyle('sec', fontName='Helvetica-Bold',
                       fontSize=11, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))
    _summary_box(elems, {
        'Patient Name':     appt['patient_name'] or '—',
        'Age / Gender':     f'{appt["age"] or "—"} yrs / {appt["gender"] or "—"}',
        'Blood Group':      appt['blood_group'] or '—',
        'Phone':            appt['patient_phone'] or '—',
        'Email':            appt['patient_email'] or '—',
        'Medical History':  (appt['medical_conditions'] or 'None')[:40],
        'Allergies':        (appt['allergies'] or 'None')[:30],
        'Insurance':        '—',
    }, LIGHT1)

    # ── Appointment info card ─────────────────────────────────────────────────
    elems.append(Paragraph(
        '<b>📅 Appointment Details</b>',
        ParagraphStyle('sec2', fontName='Helvetica-Bold',
                       fontSize=11, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))
    _summary_box(elems, {
        'Appointment ID':   f'APT-{str(aid).zfill(4)}',
        'Date':             appt['appointment_date'] or '—',
        'Time Slot':        appt['time_slot'] or '—',
        'Type':             appt['type'] or '—',
        'Status':           appt['status'].upper(),
        'Notes':            (appt['notes'] or 'None')[:50],
    }, colors.HexColor('#E8F4FF'))

    # ── Doctor info card ──────────────────────────────────────────────────────
    elems.append(Paragraph(
        '<b>👨‍⚕️ Doctor Information</b>',
        ParagraphStyle('sec3', fontName='Helvetica-Bold',
                       fontSize=11, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))
    _summary_box(elems, {
        'Doctor Name':    appt['doctor_name'] or '—',
        'Department':     appt['department'] or '—',
        'Specialization': appt['specialization'] or '—',
        'Qualification':  appt['qualification'] or '—',
        'Experience':     f'{appt["experience"] or 0} years',
        'Doctor Phone':   appt['doctor_phone'] or '—',
    }, colors.HexColor('#F0F8FF'))

    # ── EHR notes if available ────────────────────────────────────────────────
    if ehr:
        elems.append(Paragraph(
            '<b>📋 EHR / Clinical Notes (Same Visit)</b>',
            ParagraphStyle('sec4', fontName='Helvetica-Bold',
                           fontSize=11, textColor=PURPLE)
        ))
        elems.append(Spacer(1, 6))
        _summary_box(elems, {
            'Diagnosis':    (ehr['diagnosis'] or '—')[:60],
            'Prescription': (ehr['prescription'] or '—')[:60],
            'Treatment':    (ehr['treatment_history'] or '—')[:60],
            'Lab Reports':  (ehr['lab_reports'] or '—')[:60],
        }, colors.HexColor('#F0FFF4'))
    else:
        elems.append(Paragraph(
            '<font color="#7B6FA0" size="9">No EHR record found for this visit date.</font>',
            ParagraphStyle('noehr', fontSize=9, textColor=MUTED)
        ))

    elems.append(Spacer(1, 20))

    # ── Instructions box ─────────────────────────────────────────────────────
    inst = [[Paragraph(
        '<b>📌 Patient Instructions:</b><br/>'
        '• Please arrive 15 minutes before your scheduled appointment time.<br/>'
        '• Carry this document and a valid photo ID.<br/>'
        '• Bring all previous medical reports and current medications.<br/>'
        '• If you need to cancel, please inform us at least 24 hours in advance.',
        ParagraphStyle('inst', fontName='Helvetica', fontSize=8,
                       textColor=DARK, leading=14)
    )]]
    inst_tbl = Table(inst, colWidths=[17*cm])
    inst_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#FFFBF0')),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('BOX',           (0,0), (-1,-1), 1, colors.HexColor('#FFD5B8')),
        ('ROUNDEDCORNERS', [6,6,6,6]),
    ]))
    elems.append(inst_tbl)
    elems.append(Spacer(1, 16))

    # ── Footer ────────────────────────────────────────────────────────────────
    elems.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E8E0F5')))
    elems.append(Paragraph(
        f'<font color="#7B6FA0" size="8">HealthAI Smart Healthcare System | '
        f'Appointment APT-{str(aid).zfill(4)} | Confidential | '
        f'Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
        ParagraphStyle('foot', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    fname = f'appointment_{appt["patient_name"].replace(" ","_")}_{appt["appointment_date"]}.pdf'
    return send_file(buf, as_attachment=True,
                     download_name=fname, mimetype='application/pdf')


# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/reports/patient/<int:pid>/predictions')
def report_patient_predictions(pid):
    """All AI predictions for one patient as a PDF."""
    conn = get_db()
    patient = conn.execute(
        "SELECT * FROM patients WHERE id=?", (pid,)
    ).fetchone()
    if not patient:
        conn.close()
        return jsonify({"error": "Patient not found"}), 404

    preds = conn.execute("""
        SELECT pr.*, doc.name AS doctor_name
        FROM predictions pr
        LEFT JOIN doctors doc ON doc.id = 1
        WHERE pr.patient_id = ?
        ORDER BY pr.created_at DESC
    """, (pid,)).fetchall()
    conn.close()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    elems = []
    styles = getSampleStyleSheet()

    pname = patient['name']

    _pdf_header(elems, styles,
                f'🧠 AI Disease Prediction Report',
                f'Patient: {pname} | '
                f'Total Predictions: {len(preds)} | '
                f'Generated: {datetime.now().strftime("%d %b %Y")}')

    # Patient card
    elems.append(Paragraph(
        '<b>👤 Patient Profile</b>',
        ParagraphStyle('sp', fontName='Helvetica-Bold',
                       fontSize=11, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))
    _summary_box(elems, {
        'Name':            pname,
        'Age':             f'{patient["age"] or "—"} years',
        'Gender':          patient['gender'] or '—',
        'Blood Group':     patient['blood_group'] or '—',
        'Phone':           patient['phone'] or '—',
        'Medical History': (patient['medical_conditions'] or 'None')[:50],
        'Allergies':       (patient['allergies'] or 'None')[:40],
        'Total Tests':     str(len(preds)),
    }, LIGHT1)

    if not preds:
        elems.append(Paragraph(
            'No AI predictions found for this patient.',
            ParagraphStyle('emp', fontSize=10,
                           textColor=MUTED, alignment=TA_CENTER)
        ))
    else:
        # ── Summary stats ─────────────────────────────────────────────────────
        high   = sum(1 for p in preds if p['severity'] == 'High')
        medium = sum(1 for p in preds if p['severity'] == 'Medium')
        low    = sum(1 for p in preds if p['severity'] == 'Low')
        avg    = round(sum(p['risk_score'] for p in preds) / len(preds), 1)

        elems.append(Paragraph(
            '<b>📊 Summary Statistics</b>',
            ParagraphStyle('ss', fontName='Helvetica-Bold',
                           fontSize=11, textColor=PURPLE)
        ))
        elems.append(Spacer(1, 6))
        _summary_box(elems, {
            'Total Predictions': str(len(preds)),
            'Average Risk Score': f'{avg}%',
            '🔴 High Risk':      str(high),
            '🟡 Medium Risk':    str(medium),
            '🟢 Low Risk':       str(low),
            'Latest Test':       (preds[0]['created_at'] or '—')[:10],
        }, colors.HexColor('#FFF0F3'))

        # ── Risk overview bar ─────────────────────────────────────────────────
        total = len(preds)
        bar_data = [[
            Paragraph('<b>Risk breakdown:</b>',
                      ParagraphStyle('rb0', fontSize=8, textColor=DARK)),
            Paragraph(
                f'<font color="#e74c3c">■ High {high} ({round(high/total*100)}%)  </font>'
                f'<font color="#e6a817">■ Medium {medium} ({round(medium/total*100)}%)  </font>'
                f'<font color="#2d9e6a">■ Low {low} ({round(low/total*100)}%)</font>',
                ParagraphStyle('rb1', fontSize=8)),
        ]]
        bar_tbl = Table(bar_data, colWidths=[4*cm, 13*cm])
        bar_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), LIGHT2),
            ('TOPPADDING',    (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING',   (0,0), (-1,-1), 10),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elems.append(bar_tbl)
        elems.append(Spacer(1, 14))

        # ── All predictions table ─────────────────────────────────────────────
        elems.append(Paragraph(
            '<b>📋 All Prediction Records</b>',
            ParagraphStyle('pr', fontName='Helvetica-Bold',
                           fontSize=11, textColor=PURPLE)
        ))
        elems.append(Spacer(1, 6))

        def sev_clr(s):
            return {'High':'#e74c3c','Medium':'#e6a817','Low':'#2d9e6a'}.get(s,'#555')

        def risk_bar_txt(score):
            f = int(score / 10)
            return '█' * f + '░' * (10 - f)

        header = ['#','Disease','Risk Score','Severity','Recommendation','Date']
        data   = [header]
        for p in preds:
            sc = sev_clr(p['severity'])
            data.append([
                f'#{p["id"]}',
                p['predicted_disease'],
                Paragraph(
                    f'<font face="Courier" size="7" color="{sc}">'
                    f'{risk_bar_txt(p["risk_score"])}</font>'
                    f'<br/><b><font color="{sc}" size="9">{p["risk_score"]}%</font></b>',
                    ParagraphStyle('rb2', fontSize=7, leading=10)
                ),
                Paragraph(
                    f'<font color="{sc}"><b>{p["severity"]}</b></font>',
                    ParagraphStyle('sv2', fontSize=8)
                ),
                Paragraph(
                    f'<font size="7">{_recommend(p["disease_type"], p["severity"])[:70]}…</font>',
                    ParagraphStyle('rc', fontSize=7, leading=10)
                ),
                (p['created_at'] or '—')[:10],
            ])
        elems.append(_styled_table(
            data,
            [1.2*cm, 3.2*cm, 3.8*cm, 2.2*cm, 5.3*cm, 2.3*cm],
            header_bg=LAVENDER
        ))
        elems.append(Spacer(1, 14))

        # ── Individual detail card per prediction ─────────────────────────────
        elems.append(Paragraph(
            '<b>🔍 Detailed Prediction Breakdown</b>',
            ParagraphStyle('db', fontName='Helvetica-Bold',
                           fontSize=11, textColor=PURPLE)
        ))
        elems.append(Spacer(1, 8))

        for p in preds:
            sc   = sev_clr(p['severity'])
            sbg2 = {'High':'#FFE8EC','Medium':'#FFF8E0','Low':'#E8FFF4'}.get(p['severity'],'#F0EBFF')
            hbg2 = {'High': PINK,'Medium': PEACH,'Low': MINT}.get(p['severity'], PURPLE)

            # Card header
            ch = [[Paragraph(
                f'<b><font color="white">'
                f'{"🔴" if p["severity"]=="High" else "🟡" if p["severity"]=="Medium" else "🟢"} '
                f'{p["predicted_disease"]}  |  Risk: {p["risk_score"]}%  |  '
                f'Severity: {p["severity"]}  |  Date: {(p["created_at"] or "—")[:10]}'
                f'</font></b>',
                ParagraphStyle('ch2', fontName='Helvetica-Bold',
                               fontSize=9, textColor=WHITE)
            )]]
            ch_tbl = Table(ch, colWidths=[17*cm])
            ch_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), hbg2),
                ('TOPPADDING',    (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LEFTPADDING',   (0,0), (-1,-1), 12),
            ]))
            elems.append(ch_tbl)

            # Risk visual bar row
            filled_w = int(p['risk_score'] / 100 * 14)   # cm
            empty_w  = 14 - filled_w
            bar_fill_color = {'High':PINK,'Medium':PEACH,'Low':MINT}.get(p['severity'], PURPLE)

            bar_row = [[
                Paragraph('<b>Risk level:</b>',
                          ParagraphStyle('bl', fontSize=8, textColor=MUTED)),
                '',
                Paragraph(f'<b><font color="{sc}">{p["risk_score"]}%</font></b>',
                          ParagraphStyle('bp', fontSize=9)),
            ]]
            bar_tbl2 = Table(bar_row, colWidths=[3*cm, 11*cm, 3*cm])
            bar_tbl2.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor(sbg2)),
                ('TOPPADDING',    (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING',   (0,0), (-1,-1), 12),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elems.append(bar_tbl2)

            # Detail info
            rec_text = _recommend(p['disease_type'], p['severity'])
            det_rows = [[
                Paragraph('<b><font color="#7C6FD4">Disease Type:</font></b>',
                          ParagraphStyle('dk3', fontSize=8, textColor=PURPLE)),
                Paragraph(f'<font size="8">{p["predicted_disease"]}</font>',
                          ParagraphStyle('dv3', fontSize=8)),
                Paragraph('<b><font color="#7C6FD4">Test Date:</font></b>',
                          ParagraphStyle('dk4', fontSize=8, textColor=PURPLE)),
                Paragraph(f'<font size="8">{(p["created_at"] or "—")[:16]}</font>',
                          ParagraphStyle('dv4', fontSize=8)),
            ],[
                Paragraph('<b><font color="#7C6FD4">💊 Recommendation:</font></b>',
                          ParagraphStyle('dk5', fontSize=8, textColor=PURPLE)),
                Paragraph(f'<font size="8">{rec_text}</font>',
                          ParagraphStyle('dv5', fontSize=8)),
                '', '',
            ]]
            det_tbl2 = Table(det_rows, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
            det_tbl2.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor(sbg2)),
                ('TOPPADDING',    (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING',   (0,0), (-1,-1), 12),
                ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#E8E0F5')),
                ('SPAN',          (1,1), (3,1)),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elems.append(det_tbl2)
            elems.append(Spacer(1, 10))

    # ── Footer ────────────────────────────────────────────────────────────────
    elems.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E8E0F5')))
    elems.append(Paragraph(
        f'<font color="#7B6FA0" size="8">HealthAI AI Prediction Report | '
        f'Patient: {pname} | Confidential | '
        f'Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
        ParagraphStyle('foot2', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    fname = f'predictions_{pname.replace(" ","_")}_{datetime.now().strftime("%Y%m%d")}.pdf'
    return send_file(buf, as_attachment=True,
                     download_name=fname, mimetype='application/pdf')


# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/reports/patient/<int:pid>/full')
def report_patient_full(pid):
    """Complete patient report: profile + all appointments + all predictions + EHR."""
    conn = get_db()
    patient = conn.execute(
        "SELECT * FROM patients WHERE id=?", (pid,)
    ).fetchone()
    if not patient:
        conn.close()
        return jsonify({"error": "Patient not found"}), 404

    appts = conn.execute("""
        SELECT a.*, doc.name AS doctor_name, doc.department
        FROM appointments a
        LEFT JOIN doctors doc ON a.doctor_id = doc.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC
    """, (pid,)).fetchall()

    preds = conn.execute("""
        SELECT * FROM predictions
        WHERE patient_id = ?
        ORDER BY created_at DESC
    """, (pid,)).fetchall()

    ehrs = conn.execute("""
        SELECT e.*, doc.name AS doctor_name
        FROM ehr e
        LEFT JOIN doctors doc ON e.doctor_id = doc.id
        WHERE e.patient_id = ?
        ORDER BY e.visit_date DESC
    """, (pid,)).fetchall()

    conn.close()

    pname = patient['name']
    buf   = io.BytesIO()
    doc   = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=1.5*cm, rightMargin=1.5*cm,
                              topMargin=1.5*cm, bottomMargin=1.5*cm)
    elems = []
    styles = getSampleStyleSheet()

    _pdf_header(elems, styles,
                f'📁 Complete Patient Report',
                f'Patient: {pname} | '
                f'ID: P-{str(pid).zfill(4)} | '
                f'Date: {datetime.now().strftime("%d %b %Y")}')

    # Patient profile
    elems.append(Paragraph('<b>👤 Patient Profile</b>',
                           ParagraphStyle('h1', fontName='Helvetica-Bold',
                                          fontSize=12, textColor=PURPLE)))
    elems.append(Spacer(1, 6))
    _summary_box(elems, {
        'Full Name':       pname,
        'Age / Gender':    f'{patient["age"] or "—"} yrs / {patient["gender"] or "—"}',
        'Blood Group':     patient['blood_group'] or '—',
        'Phone':           patient['phone'] or '—',
        'Email':           patient['email'] or '—',
        'Allergies':       (patient['allergies'] or 'None')[:40],
        'Insurance':       (patient['insurance'] or '—')[:30],
        'Medical History': (patient['medical_conditions'] or 'None')[:50],
    }, LIGHT1)

    # Appointments section
    elems.append(Paragraph(
        f'<b>📅 Appointments ({len(appts)} total)</b>',
        ParagraphStyle('h2', fontName='Helvetica-Bold',
                       fontSize=12, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))

    if appts:
        def sc2(s):
            return {'confirmed':'#2d9e6a','pending':'#e6a817',
                    'cancelled':'#e74c3c','completed':'#5B9BD5'}.get(s,'#555')
        hdr = ['ID','Doctor','Department','Date','Time','Type','Status']
        arows = [hdr]
        for a in appts:
            arows.append([
                f'APT-{str(a["id"]).zfill(4)}',
                a['doctor_name']  or '—',
                a['department']   or '—',
                a['appointment_date'] or '—',
                a['time_slot']    or '—',
                a['type']         or '—',
                Paragraph(
                    f'<font color="{sc2(a["status"])}"><b>{a["status"].upper()}</b></font>',
                    ParagraphStyle('as', fontSize=7)
                ),
            ])
        elems.append(_styled_table(
            arows,
            [2.5*cm, 3.5*cm, 3*cm, 2.5*cm, 1.8*cm, 2.7*cm, 2.2*cm],
            header_bg=SKY
        ))
    else:
        elems.append(Paragraph('No appointments found.',
                                ParagraphStyle('ea', fontSize=9, textColor=MUTED)))
    elems.append(Spacer(1, 14))

    # EHR section
    elems.append(Paragraph(
        f'<b>📋 EHR Records ({len(ehrs)} total)</b>',
        ParagraphStyle('h3', fontName='Helvetica-Bold',
                       fontSize=12, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))

    if ehrs:
        hdr2 = ['Date','Doctor','Diagnosis','Prescription','Treatment']
        erows = [hdr2]
        for e in ehrs:
            erows.append([
                e['visit_date'] or '—',
                e['doctor_name'] or '—',
                Paragraph(f'<font size="7">{(e["diagnosis"] or "—")[:40]}</font>',
                          ParagraphStyle('ed', fontSize=7)),
                Paragraph(f'<font size="7">{(e["prescription"] or "—")[:40]}</font>',
                          ParagraphStyle('ep', fontSize=7)),
                Paragraph(f'<font size="7">{(e["treatment_history"] or "—")[:30]}</font>',
                          ParagraphStyle('et', fontSize=7)),
            ])
        elems.append(_styled_table(
            erows,
            [2.2*cm, 3*cm, 4.5*cm, 4.5*cm, 3.3*cm],
            header_bg=MINT
        ))
    else:
        elems.append(Paragraph('No EHR records found.',
                                ParagraphStyle('ee', fontSize=9, textColor=MUTED)))
    elems.append(Spacer(1, 14))

    # Predictions section
    elems.append(Paragraph(
        f'<b>🧠 AI Predictions ({len(preds)} total)</b>',
        ParagraphStyle('h4', fontName='Helvetica-Bold',
                       fontSize=12, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))

    if preds:
        def svc(s):
            return {'High':'#e74c3c','Medium':'#e6a817','Low':'#2d9e6a'}.get(s,'#555')
        hdr3 = ['Disease','Risk %','Severity','Recommendation','Date']
        prows = [hdr3]
        for p in preds:
            prows.append([
                p['predicted_disease'],
                Paragraph(
                    f'<font color="{svc(p["severity"])}" size="10"><b>{p["risk_score"]}%</b></font>',
                    ParagraphStyle('rs2', fontSize=9)
                ),
                Paragraph(
                    f'<font color="{svc(p["severity"])}"><b>{p["severity"]}</b></font>',
                    ParagraphStyle('sv3', fontSize=8)
                ),
                Paragraph(
                    f'<font size="7">{_recommend(p["disease_type"], p["severity"])[:65]}…</font>',
                    ParagraphStyle('rc2', fontSize=7, leading=10)
                ),
                (p['created_at'] or '—')[:10],
            ])
        elems.append(_styled_table(
            prows,
            [3.5*cm, 2*cm, 2.2*cm, 7*cm, 2.3*cm],
            header_bg=LAVENDER
        ))
    else:
        elems.append(Paragraph('No predictions found.',
                                ParagraphStyle('ep2', fontSize=9, textColor=MUTED)))

    elems.append(Spacer(1, 20))
    elems.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E8E0F5')))
    elems.append(Paragraph(
        f'<font color="#7B6FA0" size="8">HealthAI Complete Patient Report | '
        f'Patient: {pname} (P-{str(pid).zfill(4)}) | Confidential | '
        f'Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
        ParagraphStyle('foot3', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    fname = f'full_report_{pname.replace(" ","_")}_{datetime.now().strftime("%Y%m%d")}.pdf'
    return send_file(buf, as_attachment=True,
                     download_name=fname, mimetype='application/pdf')
# ═══════════════════════════════════════════════════════════════════════════════
# EHR INDIVIDUAL PDF ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/reports/ehr/<int:eid>')
def report_single_ehr(eid):
    """PDF for one specific EHR record."""
    conn = get_db()
    record = conn.execute("""
        SELECT e.*,
               p.name AS patient_name, p.age, p.gender, p.blood_group,
               p.phone AS patient_phone, p.email AS patient_email,
               p.medical_conditions, p.allergies, p.insurance,
               doc.name AS doctor_name, doc.department,
               doc.specialization, doc.qualification, doc.experience,
               doc.phone AS doctor_phone
        FROM ehr e
        LEFT JOIN patients p   ON e.patient_id = p.id
        LEFT JOIN doctors  doc ON e.doctor_id  = doc.id
        WHERE e.id = ?
    """, (eid,)).fetchone()

    if not record:
        conn.close()
        return jsonify({"error": "EHR record not found"}), 404

    # Get all previous EHR records for same patient
    history = conn.execute("""
        SELECT e.*, doc.name AS doctor_name
        FROM ehr e
        LEFT JOIN doctors doc ON e.doctor_id = doc.id
        WHERE e.patient_id = ? AND e.id != ?
        ORDER BY e.visit_date DESC
        LIMIT 5
    """, (record['patient_id'], eid)).fetchall()

    conn.close()

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
    elems  = []
    styles = getSampleStyleSheet()

    _pdf_header(elems, styles,
                '📋 Electronic Health Record',
                f'EHR-{str(eid).zfill(4)} | '
                f'Patient: {record["patient_name"]} | '
                f'Visit: {record["visit_date"]}')

    # ── Patient card ──────────────────────────────────────────────────────────
    elems.append(Paragraph(
        '<b>👤 Patient Information</b>',
        ParagraphStyle('h1', fontName='Helvetica-Bold',
                       fontSize=11, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))
    _summary_box(elems, {
        'Patient Name':    record['patient_name'] or '—',
        'Age / Gender':    f'{record["age"] or "—"} yrs / {record["gender"] or "—"}',
        'Blood Group':     record['blood_group'] or '—',
        'Phone':           record['patient_phone'] or '—',
        'Email':           record['patient_email'] or '—',
        'Allergies':       (record['allergies'] or 'None')[:40],
        'Insurance':       (record['insurance'] or '—')[:30],
        'Known Conditions':(record['medical_conditions'] or 'None')[:50],
    }, LIGHT1)

    # ── Doctor card ───────────────────────────────────────────────────────────
    elems.append(Paragraph(
        '<b>👨‍⚕️ Treating Doctor</b>',
        ParagraphStyle('h2', fontName='Helvetica-Bold',
                       fontSize=11, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))
    _summary_box(elems, {
        'Doctor Name':    record['doctor_name'] or '—',
        'Department':     record['department'] or '—',
        'Specialization': record['specialization'] or '—',
        'Qualification':  record['qualification'] or '—',
        'Experience':     f'{record["experience"] or 0} years',
        'Visit Date':     record['visit_date'] or '—',
    }, colors.HexColor('#F0F8FF'))

    # ── Clinical details ──────────────────────────────────────────────────────
    elems.append(Paragraph(
        '<b>🩺 Clinical Details</b>',
        ParagraphStyle('h3', fontName='Helvetica-Bold',
                       fontSize=11, textColor=PURPLE)
    ))
    elems.append(Spacer(1, 6))

    def clinical_block(label, content, bg):
        tbl = Table([[
            Paragraph(f'<b><font color="#7C6FD4">{label}</font></b>',
                      ParagraphStyle('cl', fontName='Helvetica-Bold',
                                     fontSize=9, textColor=PURPLE)),
            Paragraph(f'<font size="9">{content or "—"}</font>',
                      ParagraphStyle('cv', fontName='Helvetica', fontSize=9, leading=13)),
        ]], colWidths=[4*cm, 13*cm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), bg),
            ('TOPPADDING',    (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 9),
            ('LEFTPADDING',   (0,0), (-1,-1), 12),
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('GRID',          (0,0), (-1,-1), 0.3,
             colors.HexColor('#E8E0F5')),
        ]))
        return tbl

    elems.append(clinical_block(
        '🔍 Diagnosis',
        record['diagnosis'],
        colors.HexColor('#FFF0F3')
    ))
    elems.append(Spacer(1, 4))
    elems.append(clinical_block(
        '💊 Prescription',
        record['prescription'],
        colors.HexColor('#F0FFF4')
    ))
    elems.append(Spacer(1, 4))
    elems.append(clinical_block(
        '🏥 Treatment Plan',
        record['treatment_history'],
        colors.HexColor('#F0F8FF')
    ))
    elems.append(Spacer(1, 4))
    elems.append(clinical_block(
        '🔬 Lab Reports',
        record['lab_reports'],
        colors.HexColor('#FFFBF0')
    ))
    elems.append(Spacer(1, 14))

    # ── Visit history ─────────────────────────────────────────────────────────
    if history:
        elems.append(Paragraph(
            '<b>📅 Previous Visits (last 5)</b>',
            ParagraphStyle('h4', fontName='Helvetica-Bold',
                           fontSize=11, textColor=PURPLE)
        ))
        elems.append(Spacer(1, 6))
        hdr = ['Visit Date', 'Doctor', 'Diagnosis', 'Prescription']
        rows = [hdr]
        for h in history:
            rows.append([
                h['visit_date'] or '—',
                h['doctor_name'] or '—',
                Paragraph(f'<font size="7">{(h["diagnosis"] or "—")[:50]}</font>',
                          ParagraphStyle('hd', fontSize=7)),
                Paragraph(f'<font size="7">{(h["prescription"] or "—")[:50]}</font>',
                          ParagraphStyle('hp', fontSize=7)),
            ])
        elems.append(_styled_table(
            rows,
            [2.8*cm, 3.5*cm, 5.5*cm, 5.2*cm],
            header_bg=MINT
        ))
        elems.append(Spacer(1, 14))

    # ── Instructions ──────────────────────────────────────────────────────────
    inst = [[Paragraph(
        '<b>📌 Follow-up Instructions:</b><br/>'
        '• Take all medications as prescribed. Do not skip doses.<br/>'
        '• Return immediately if symptoms worsen or new symptoms appear.<br/>'
        '• Keep this document for your medical records.<br/>'
        '• Schedule your next follow-up appointment as advised.',
        ParagraphStyle('inst', fontName='Helvetica',
                       fontSize=8, textColor=DARK, leading=14)
    )]]
    inst_tbl = Table(inst, colWidths=[17*cm])
    inst_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#FFFBF0')),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('BOX',           (0,0), (-1,-1), 1, colors.HexColor('#FFD5B8')),
    ]))
    elems.append(inst_tbl)
    elems.append(Spacer(1, 16))

    # ── Footer ────────────────────────────────────────────────────────────────
    elems.append(HRFlowable(width='100%', thickness=0.5,
                             color=colors.HexColor('#E8E0F5')))
    elems.append(Paragraph(
        f'<font color="#7B6FA0" size="8">HealthAI EHR | '
        f'Record EHR-{str(eid).zfill(4)} | Patient: {record["patient_name"]} | '
        f'Confidential | Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
        ParagraphStyle('foot', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    fname = (f'EHR_{record["patient_name"].replace(" ","_")}'
             f'_{record["visit_date"]}.pdf')
    return send_file(buf, as_attachment=True,
                     download_name=fname, mimetype='application/pdf')


@app.route('/api/reports/patient/<int:pid>/ehr')
def report_patient_all_ehr(pid):
    """All EHR records for one patient as a single PDF."""
    conn = get_db()
    patient = conn.execute(
        "SELECT * FROM patients WHERE id=?", (pid,)
    ).fetchone()
    if not patient:
        conn.close()
        return jsonify({"error": "Patient not found"}), 404

    records = conn.execute("""
        SELECT e.*, doc.name AS doctor_name,
               doc.department, doc.specialization
        FROM ehr e
        LEFT JOIN doctors doc ON e.doctor_id = doc.id
        WHERE e.patient_id = ?
        ORDER BY e.visit_date DESC
    """, (pid,)).fetchall()
    conn.close()

    pname  = patient['name']
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=1.5*cm, rightMargin=1.5*cm,
                               topMargin=1.5*cm, bottomMargin=1.5*cm)
    elems  = []
    styles = getSampleStyleSheet()

    _pdf_header(elems, styles,
                f'📋 Complete EHR — {pname}',
                f'Patient ID: P-{str(pid).zfill(4)} | '
                f'Total Records: {len(records)} | '
                f'Generated: {datetime.now().strftime("%d %b %Y")}')

    # Patient summary
    _summary_box(elems, {
        'Name':        pname,
        'Age':         f'{patient["age"] or "—"} years',
        'Gender':      patient['gender'] or '—',
        'Blood Group': patient['blood_group'] or '—',
        'Phone':       patient['phone'] or '—',
        'Allergies':   (patient['allergies'] or 'None')[:40],
        'Conditions':  (patient['medical_conditions'] or 'None')[:50],
        'Records':     str(len(records)),
    }, LIGHT1)

    if not records:
        elems.append(Paragraph(
            'No EHR records found for this patient.',
            ParagraphStyle('emp', fontSize=10,
                           textColor=MUTED, alignment=TA_CENTER)
        ))
    else:
        for i, r in enumerate(records):
            # Section divider
            elems.append(Paragraph(
                f'<b>Visit {i+1} — {r["visit_date"] or "—"}</b>',
                ParagraphStyle(f'vt{i}', fontName='Helvetica-Bold',
                               fontSize=10, textColor=PURPLE)
            ))
            elems.append(Spacer(1, 4))

            _summary_box(elems, {
                'Doctor':         r['doctor_name'] or '—',
                'Department':     r['department'] or '—',
                'Specialization': r['specialization'] or '—',
                'Record ID':      f'EHR-{str(r["id"]).zfill(4)}',
            }, colors.HexColor('#F0F8FF'))

            blocks = [
                ('🔍 Diagnosis',    r['diagnosis'],        '#FFF0F3'),
                ('💊 Prescription', r['prescription'],     '#F0FFF4'),
                ('🏥 Treatment',    r['treatment_history'],'#F0F8FF'),
                ('🔬 Lab Reports',  r['lab_reports'],      '#FFFBF0'),
            ]
            for label, content, bg in blocks:
                if content and content.strip():
                    tbl = Table([[
                        Paragraph(
                            f'<b><font color="#7C6FD4">{label}</font></b>',
                            ParagraphStyle(f'lbl{i}', fontName='Helvetica-Bold',
                                           fontSize=8, textColor=PURPLE)
                        ),
                        Paragraph(
                            f'<font size="8">{content}</font>',
                            ParagraphStyle(f'val{i}', fontSize=8, leading=12)
                        ),
                    ]], colWidths=[3.5*cm, 13.5*cm])
                    tbl.setStyle(TableStyle([
                        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor(bg)),
                        ('TOPPADDING',    (0,0), (-1,-1), 7),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                        ('LEFTPADDING',   (0,0), (-1,-1), 10),
                        ('GRID',          (0,0), (-1,-1), 0.3,
                         colors.HexColor('#E8E0F5')),
                        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                    ]))
                    elems.append(tbl)
                    elems.append(Spacer(1, 3))

            elems.append(HRFlowable(width='100%', thickness=0.4,
                                     color=colors.HexColor('#E8E0F5')))
            elems.append(Spacer(1, 10))

    elems.append(Paragraph(
        f'<font color="#7B6FA0" size="8">HealthAI EHR Report | '
        f'Patient: {pname} | Confidential | '
        f'Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</font>',
        ParagraphStyle('foot2', alignment=TA_CENTER, fontSize=8, textColor=MUTED)
    ))

    doc.build(elems)
    buf.seek(0)
    fname = f'EHR_all_{pname.replace(" ","_")}_{datetime.now().strftime("%Y%m%d")}.pdf'
    return send_file(buf, as_attachment=True,
                     download_name=fname, mimetype='application/pdf')
# ── NEW PAGE ROUTES FOR 3 DASHBOARDS ─────────────────────────────────────────
@app.route('/admin-login')
def admin_login_page():
    return send_from_directory(FRONT, 'admin_login.html')

@app.route('/admin-dashboard')
def admin_dashboard_page():
    return send_from_directory(FRONT, 'admin_dashboard.html')

@app.route('/patient-login')
def patient_login_page():
    return send_from_directory(FRONT, 'patient_login.html')

@app.route('/patient-dashboard')
def patient_dashboard_page():
    return send_from_directory(FRONT, 'patient_dashboard.html')

# ── PATIENT-SPECIFIC API ROUTES ───────────────────────────────────────────────
@app.route('/api/my/profile/<int:uid>', methods=['GET'])
def my_profile(uid):
    conn = get_db()
    p = conn.execute(
        "SELECT * FROM patients WHERE user_id=?", (uid,)
    ).fetchone()
    conn.close()
    return jsonify(dict(p)) if p else jsonify({}), 404

@app.route('/api/my/appointments/<int:pid>', methods=['GET'])
def my_appointments(pid):
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*,
               doc.name        AS doctor_name,
               doc.department  AS department,
               doc.specialization,
               doc.phone       AS doctor_phone,
               doc.qualification
        FROM appointments a
        LEFT JOIN doctors doc ON a.doctor_id = doc.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/my/ehr/<int:pid>', methods=['GET'])
def my_ehr(pid):
    conn = get_db()
    rows = conn.execute("""
        SELECT e.*,
               doc.name           AS doctor_name,
               doc.department,
               doc.specialization
        FROM ehr e
        LEFT JOIN doctors doc ON e.doctor_id = doc.id
        WHERE e.patient_id = ?
        ORDER BY e.visit_date DESC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/my/predictions/<int:pid>', methods=['GET'])
def my_predictions(pid):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM predictions
        WHERE patient_id = ?
        ORDER BY created_at DESC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/my/book-appointment', methods=['POST'])
def my_book_appointment():
    d = request.json
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO appointments
            (patient_id,doctor_id,appointment_date,time_slot,notes,status,type)
            VALUES (?,?,?,?,?,?,?)
        """, (
            d['patient_id'], d['doctor_id'], d['date'],
            d.get('slot','9AM'), d.get('notes',''),
            'pending', d.get('type','Regular Checkup')
        ))
        conn.commit()
        doc = conn.execute(
            "SELECT name FROM doctors WHERE id=?", (d['doctor_id'],)
        ).fetchone()
        pat = conn.execute(
            "SELECT name FROM patients WHERE id=?", (d['patient_id'],)
        ).fetchone()
        dname = doc['name'] if doc else f"Doctor #{d['doctor_id']}"
        pname = pat['name'] if pat else f"Patient #{d['patient_id']}"
        _add_notification(conn,
            f"New appointment: {pname} with {dname} on {d['date']}",
            'success')
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        conn.close()
if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print("⚠️ Database not found. Run: python database/init_db.py")

    if not os.path.exists(ML_PATH):
        print("⚠️ ML models not found. Run: python ml_models/train_models.py")

    print("🚀 Starting HealthAI Flask server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)