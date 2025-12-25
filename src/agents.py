from typing import Dict, Any
from src.db import find_doctors, get_available_slots, book_appointment, add_record, get_patient_records
from src.tools import parse_date_hint, pick_time_window

def appointment_agent(db_path: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
    patient = extracted.get("patient_name") or "Patient"
    specialty = extracted.get("specialty")
    doctor_name = extracted.get("doctor")
    date_hint = extracted.get("date_hint")
    time_hint = extracted.get("time_hint")
    reason = extracted.get("symptoms/topic") or extracted.get("topic") or "Consultation"

    doctors = find_doctors(db_path, specialty=specialty) if specialty else find_doctors(db_path, specialty=None)
    chosen = None
    if doctor_name and doctors:
        for d in doctors:
            if doctor_name.lower() in d["name"].lower():
                chosen = d
                break
    if not chosen and doctors:
        chosen = doctors[0]
    if not chosen:
        return {"ok": False, "message": "No doctors found. Seed demo data first.", "patient": patient}

    day_iso = parse_date_hint(date_hint)
    start_hour, end_hour = pick_time_window(time_hint)
    slots = get_available_slots(db_path, chosen["doctor_id"], day_iso, start_hour=start_hour, end_hour=end_hour, slot_minutes=30)

    if not slots:
        return {"ok": False, "message": "No available slots found for that day/time window.", "doctor": chosen, "day": day_iso}

    s = slots[0]
    appt = book_appointment(db_path, patient, chosen["doctor_id"], s["start_time"], s["end_time"], reason=reason)
    return {"ok": True, "action": "book_appointment", "appointment": appt, "doctor": chosen, "day": day_iso}

def records_agent(db_path: str, extracted: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    patient = extracted.get("patient_name") or "Patient"
    rec = add_record(db_path, patient, "Note", user_message, source="chat_update")
    return {"ok": True, "action": "update_records", "record": rec}

def history_agent(db_path: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
    patient = extracted.get("patient_name") or "Patient"
    records = get_patient_records(db_path, patient, limit=25)
    if not records:
        return {"ok": False, "action": "retrieve_history", "patient": patient, "message": "No records found for this patient."}
    return {"ok": True, "action": "retrieve_history", "patient": patient, "records": records}
