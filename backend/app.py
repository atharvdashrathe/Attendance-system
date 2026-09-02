"""
app.py — Flask REST API for the Classroom Attendance System

Endpoints:
    GET  /api/dashboard
    GET  /api/students
    GET  /api/subjects
    POST /api/subjects
    DELETE /api/subjects/<id>
    POST /api/attendance/process
    POST /api/attendance/finalize
    GET  /api/sessions
    GET  /api/sessions/<id>
    GET  /api/sessions/<id>/excel
    GET  /api/excel/list
    GET  /api/excel/download/<filename>
    GET  /                          → serves frontend
"""

import os
import sys
import uuid
import datetime

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
import excel as xl
from attendance import process_images

# --------------------------------------------------
# App setup
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
EXCEL_DIR = os.path.join(BASE_DIR, "excel_exports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXCEL_DIR, exist_ok=True)

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)
CORS(app)

# Increase upload limit to 50 MB (classroom photos can be large)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --------------------------------------------------
# Serve frontend
# --------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# --------------------------------------------------
# Dashboard
# --------------------------------------------------

@app.route("/api/dashboard")
def dashboard():
    try:
        stats = db.get_dashboard_stats()
        return jsonify({"ok": True, "data": stats})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------
# Students
# --------------------------------------------------

@app.route("/api/students")
def students():
    try:
        rows = db.get_students()
        return jsonify({"ok": True, "data": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------
# Subjects
# --------------------------------------------------

@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    try:
        rows = db.get_subjects()
        return jsonify({"ok": True, "data": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/subjects", methods=["POST"])
def add_subject():
    try:
        data = request.get_json()
        name = (data or {}).get("name", "").strip()
        if not name:
            return jsonify({"ok": False, "error": "Subject name is required"}), 400
        new_id = db.add_subject(name)
        return jsonify({"ok": True, "id": new_id, "name": name})
    except Exception as e:
        if "Duplicate" in str(e):
            return jsonify({"ok": False, "error": "Subject already exists"}), 409
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
def delete_subject(subject_id):
    try:
        success = db.delete_subject(subject_id)
        if success:
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Subject not found"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------
# Process attendance (upload images → recognition)
# --------------------------------------------------

@app.route("/api/attendance/process", methods=["POST"])
def process_attendance():
    try:
        files = request.files.getlist("images")

        if len(files) < 1:
            return jsonify({"ok": False, "error": "At least 1 image is required"}), 400

        if len(files) > 4:
            return jsonify({"ok": False, "error": "Maximum 4 images allowed"}), 400

        # Save uploaded images to temp location
        session_token = str(uuid.uuid4())[:8]
        saved_paths = []

        for i, file in enumerate(files):
            if not file or not allowed_file(file.filename):
                return jsonify({"ok": False, "error": f"File {i+1} is not a valid image"}), 400

            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = f"{session_token}_{i}.{ext}"
            path = os.path.join(UPLOAD_DIR, filename)
            file.save(path)
            saved_paths.append(path)

        # Run recognition
        result = process_images(saved_paths)

        # Enrich records with student names
        students_map = {s["roll_no"]: s["name"] for s in db.get_students()}
        for rec in result["records"]:
            rec["name"] = students_map.get(rec["roll_no"], rec["roll_no"])

        # Clean up uploaded files
        for path in saved_paths:
            try:
                os.remove(path)
            except Exception:
                pass

        return jsonify({
            "ok": True,
            "data": {
                "records": result["records"],
                "total_faces_detected": sum(
                    len(img) for img in result["image_results"]
                ),
                "images_processed": len(saved_paths)
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------
# Finalize attendance (save to DB + Excel)
# --------------------------------------------------

@app.route("/api/attendance/finalize", methods=["POST"])
def finalize_attendance():
    try:
        data = request.get_json()

        subject_id   = data.get("subject_id")
        subject_name = data.get("subject_name", "").strip()
        lecture      = data.get("lecture", "").strip()
        date_str     = data.get("date", "").strip()
        time_str     = data.get("time", "").strip()
        records      = data.get("records", [])   # [{roll_no, status, confidence, manually_edited}]

        if not subject_id or not subject_name:
            return jsonify({"ok": False, "error": "Subject is required"}), 400
        if not lecture:
            return jsonify({"ok": False, "error": "Lecture is required"}), 400
        if not date_str:
            return jsonify({"ok": False, "error": "Date is required"}), 400
        if not time_str:
            return jsonify({"ok": False, "error": "Time is required"}), 400
        if not records:
            return jsonify({"ok": False, "error": "Attendance records are required"}), 400

        # Create session
        session_id = db.create_session(
            subject_id, subject_name, lecture, date_str, time_str
        )

        # Save records
        db.save_attendance_records(session_id, records)

        # Write to Excel
        students_map = {s["roll_no"]: s["name"] for s in db.get_students()}
        excel_records = []
        for rec in records:
            excel_records.append({
                "roll_no": rec["roll_no"],
                "name": students_map.get(rec["roll_no"], rec["roll_no"]),
                "status": rec["status"],
                "confidence": rec.get("confidence"),
                "manually_edited": rec.get("manually_edited", False)
            })

        file_path = xl.write_session_to_excel(
            subject_name, lecture, date_str, time_str, excel_records
        )

        filename = os.path.basename(file_path)

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "excel_file": filename,
            "message": "Attendance finalized successfully."
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------
# Sessions
# --------------------------------------------------

@app.route("/api/sessions")
def get_sessions():
    try:
        rows = db.get_sessions()
        return jsonify({"ok": True, "data": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sessions/<int:session_id>")
def get_session(session_id):
    try:
        session = db.get_session(session_id)
        if not session:
            return jsonify({"ok": False, "error": "Session not found"}), 404

        records = db.get_session_records(session_id)
        return jsonify({
            "ok": True,
            "data": {
                "session": session,
                "records": records
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------
# Excel download
# --------------------------------------------------

@app.route("/api/sessions/<int:session_id>/excel")
def download_session_excel(session_id):
    try:
        session = db.get_session(session_id)
        if not session:
            return jsonify({"ok": False, "error": "Session not found"}), 404

        subject_name = session["subject_name"]
        file_path = xl.get_subject_excel_path(subject_name)

        if not os.path.exists(file_path):
            return jsonify({"ok": False, "error": "Excel file not found"}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/excel/list")
def list_excel():
    try:
        files = xl.list_excel_files()
        return jsonify({"ok": True, "data": files})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/excel/download/<path:filename>")
def download_excel(filename):
    try:
        safe_name = os.path.basename(filename)
        file_path = os.path.join(EXCEL_DIR, safe_name)
        if not os.path.exists(file_path):
            return jsonify({"ok": False, "error": "File not found"}), 404
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------
# Main
# --------------------------------------------------

# app.py is started via run.py which handles DB init and model loading.
# Direct execution (python backend/app.py) is also supported:
if __name__ == "__main__":
    import os, sys
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("\n[app] Initialising database...")
    db.init_db()
    from recognize import load_known_faces
    load_known_faces()
    print("[app] Starting server at http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
