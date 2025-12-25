import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import re

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
  patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE,
  dob TEXT,
  gender TEXT,
  phone TEXT,
  email TEXT
);

CREATE TABLE IF NOT EXISTS patient_records (
  record_id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER,
  created_at TEXT,
  record_type TEXT,
  content TEXT,
  source TEXT,
  FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS doctors (
  doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  specialty TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
  appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER,
  doctor_id INTEGER,
  start_time TEXT,
  end_time TEXT,
  status TEXT,
  reason TEXT,
  created_at TEXT,
  FOREIGN KEY(patient_id) REFERENCES patients(patient_id),
  FOREIGN KEY(doctor_id) REFERENCES doctors(doctor_id)
);
"""

def init_db(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()

def _now():
    return datetime.utcnow().replace(microsecond=0).isoformat()

def upsert_patient(db_path: str, name: str, dob: str=None, gender: str=None, phone: str=None, email: str=None) -> int:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO patients(name, dob, gender, phone, email) VALUES (?,?,?,?,?)",
            (name, dob, gender, phone, email)
        )
        conn.commit()
        cur = conn.execute("SELECT patient_id FROM patients WHERE name=?", (name,))
        return int(cur.fetchone()[0])

def add_record(db_path: str, patient_name: str, record_type: str, content: str, source: str="manual") -> Dict[str, Any]:
    pid = upsert_patient(db_path, patient_name)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO patient_records(patient_id, created_at, record_type, content, source) VALUES (?,?,?,?,?)",
            (pid, _now(), record_type, content, source)
        )
        conn.commit()
    return {"patient": patient_name, "record_type": record_type, "status": "added"}

def get_patient_records(db_path: str, patient_name: str, limit: int=50):
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT patient_id FROM patients WHERE name=?", (patient_name,))
        row = cur.fetchone()
        if not row:
            return []
        pid = row[0]
        cur = conn.execute(
            "SELECT created_at, record_type, content, source FROM patient_records WHERE patient_id=? ORDER BY created_at DESC LIMIT ?",
            (pid, limit)
        )
        rows = cur.fetchall()
    return [{"created_at": r[0], "record_type": r[1], "content": r[2], "source": r[3]} for r in rows]

def find_doctors(db_path: str, specialty: str=None):
    q = "SELECT doctor_id, name, specialty FROM doctors"
    params = ()
    if specialty:
        q += " WHERE lower(specialty)=lower(?)"
        params = (specialty,)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(q, params)
        rows = cur.fetchall()
    return [{"doctor_id": r[0], "name": r[1], "specialty": r[2]} for r in rows]

def list_patients(db_path: str, limit: int=100):
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT patient_id, name, dob, gender FROM patients ORDER BY name LIMIT ?", (limit,))
        rows = cur.fetchall()
    return [{"patient_id": r[0], "name": r[1], "dob": r[2], "gender": r[3]} for r in rows]

def list_appointments(db_path: str, limit: int=100):
    q = """
    SELECT a.appointment_id, p.name, d.name, d.specialty, a.start_time, a.end_time, a.status, a.reason
    FROM appointments a
    JOIN patients p ON p.patient_id=a.patient_id
    JOIN doctors d ON d.doctor_id=a.doctor_id
    ORDER BY a.start_time DESC
    LIMIT ?
    """
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(q, (limit,))
        rows = cur.fetchall()
    return [{
        "appointment_id": r[0],
        "patient": r[1],
        "doctor": r[2],
        "specialty": r[3],
        "start_time": r[4],
        "end_time": r[5],
        "status": r[6],
        "reason": r[7],
    } for r in rows]

def get_available_slots(db_path: str, doctor_id: int, day_iso: str, start_hour: int=9, end_hour: int=17, slot_minutes: int=30):
    day = datetime.fromisoformat(day_iso)
    slots = []
    start = day.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end = day.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT start_time, end_time FROM appointments WHERE doctor_id=? AND start_time LIKE ?",
            (doctor_id, f"{day_iso}%")
        )
        booked = [(datetime.fromisoformat(r[0]), datetime.fromisoformat(r[1])) for r in cur.fetchall()]
    t = start
    delta = timedelta(minutes=slot_minutes)
    while t + delta <= end:
        cand = (t, t+delta)
        overlap = any(not (cand[1] <= b0 or cand[0] >= b1) for b0, b1 in booked)
        if not overlap:
            slots.append({"start_time": cand[0].isoformat(), "end_time": cand[1].isoformat()})
        t += delta
    return slots

def book_appointment(db_path: str, patient_name: str, doctor_id: int, start_time: str, end_time: str, reason: str=""):
    pid = upsert_patient(db_path, patient_name)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO appointments(patient_id, doctor_id, start_time, end_time, status, reason, created_at) VALUES (?,?,?,?,?,?,?)",
            (pid, doctor_id, start_time, end_time, "Booked", reason, _now())
        )
        conn.commit()
        appt_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    return {"appointment_id": appt_id, "patient": patient_name, "doctor_id": doctor_id, "start_time": start_time, "end_time": end_time, "status": "Booked"}

def seed_demo_data(db_path: str, pdf_sources_dir: str, records_xlsx: str=None):
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        if conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] == 0:
            conn.executemany("INSERT INTO doctors(name, specialty) VALUES (?,?)", [
                ("Dr. Smith", "Cardiology"),
                ("Dr. Patel", "Dermatology"),
                ("Dr. Chen", "General Medicine"),
                ("Dr. Rao", "Endocrinology"),
            ])
            conn.commit()

    import os
    from pypdf import PdfReader
    if os.path.isdir(pdf_sources_dir):
        for fn in os.listdir(pdf_sources_dir):
            if not fn.lower().endswith(".pdf"):
                continue
            m = re.search(r"sample_report[_-]([a-zA-Z]+)", fn, re.IGNORECASE)
            if not m:
                continue
            name = m.group(1).capitalize()
            upsert_patient(db_path, name)
            try:
                reader = PdfReader(str(Path(pdf_sources_dir)/fn))
                text = "\n".join((p.extract_text() or "") for p in reader.pages)[:8000]
                if text.strip():
                    add_record(db_path, name, "ImportedReport", text, source=fn)
            except Exception:
                pass

    with sqlite3.connect(db_path) as conn:
        if conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0] == 0:
            doc = conn.execute("SELECT doctor_id FROM doctors ORDER BY doctor_id LIMIT 1").fetchone()
            pat = conn.execute("SELECT patient_id, name FROM patients ORDER BY patient_id LIMIT 1").fetchone()
            if doc and pat:
                doctor_id = doc[0]
                patient_name = pat[1]
                start = (datetime.utcnow() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
                end = start + timedelta(minutes=30)
                conn.execute(
                    "INSERT INTO appointments(patient_id, doctor_id, start_time, end_time, status, reason, created_at) VALUES (?,?,?,?,?,?,?)",
                    (pat[0], doctor_id, start.isoformat(), end.isoformat(), "Booked", "Routine checkup", _now())
                )
                conn.commit()
