"""
database.py — MySQL database layer

Tables:
    subjects              — manageable subject list
    students              — registered students (from CleanDataset)
    attendance_sessions   — one record per attendance session
    attendance_records    — one record per student per session
"""

import mysql.connector
import os
import sys

# --------------------------------------------------
# Connection settings
# --------------------------------------------------

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "4537",
    "database": "attendance_db"
}


def get_connection():
    """Return a fresh MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)


# --------------------------------------------------
# Initialise database and tables
# --------------------------------------------------

def init_db():
    """
    Create the database and all tables if they don't exist.
    Also seeds students from CleanDataset.
    """
    # First connect without specifying the database to create it
    cfg_no_db = dict(DB_CONFIG)
    cfg_no_db.pop("database")

    conn = mysql.connector.connect(**cfg_no_db)
    cur = conn.cursor()

    cur.execute("CREATE DATABASE IF NOT EXISTS attendance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("USE attendance_db")

    # subjects
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE
        )
    """)

    # students
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            roll_no VARCHAR(20) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL
        )
    """)

    # attendance_sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject_id INT NOT NULL,
            subject_name VARCHAR(100) NOT NULL,
            lecture VARCHAR(100) NOT NULL,
            date DATE NOT NULL,
            session_time TIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)

    # attendance_records
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id INT NOT NULL,
            roll_no VARCHAR(20) NOT NULL,
            status ENUM('Present', 'Absent') NOT NULL,
            confidence FLOAT,
            manually_edited TINYINT(1) DEFAULT 0,
            UNIQUE KEY unique_session_student (session_id, roll_no),
            FOREIGN KEY (session_id) REFERENCES attendance_sessions(id)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

    # Seed students from CleanDataset
    _seed_students()


def _seed_students():
    """
    Scan CleanDataset and insert any new roll numbers into the students table.
    Does nothing for already-existing entries.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_path = os.path.join(base_dir, "CleanDataset")

    if not os.path.isdir(dataset_path):
        return

    conn = get_connection()
    cur = conn.cursor()

    for roll_no in sorted(os.listdir(dataset_path)):
        folder = os.path.join(dataset_path, roll_no)
        if not os.path.isdir(folder):
            continue

        default_name = f"Student {roll_no}"

        cur.execute("""
            INSERT IGNORE INTO students (roll_no, name)
            VALUES (%s, %s)
        """, (roll_no, default_name))

    conn.commit()
    cur.close()
    conn.close()


# --------------------------------------------------
# Subjects
# --------------------------------------------------

def get_subjects():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM subjects ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def add_subject(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO subjects (name) VALUES (%s)", (name.strip(),))
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    conn.close()
    return new_id


def delete_subject(subject_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
    conn.commit()
    affected = cur.rowcount
    cur.close()
    conn.close()
    return affected > 0


# --------------------------------------------------
# Students
# --------------------------------------------------

def get_students():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, roll_no, name FROM students ORDER BY CAST(roll_no AS UNSIGNED)")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_student_name(roll_no):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT name FROM students WHERE roll_no = %s", (roll_no,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["name"] if row else roll_no


# --------------------------------------------------
# Sessions
# --------------------------------------------------

def create_session(subject_id, subject_name, lecture, date, session_time):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO attendance_sessions
            (subject_id, subject_name, lecture, date, session_time)
        VALUES (%s, %s, %s, %s, %s)
    """, (subject_id, subject_name, lecture, date, session_time))
    conn.commit()
    session_id = cur.lastrowid
    cur.close()
    conn.close()
    return session_id


def get_sessions():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT
            s.id,
            s.subject_name,
            s.lecture,
            s.date,
            s.session_time,
            s.created_at,
            SUM(CASE WHEN r.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            COUNT(r.id) AS total_count
        FROM attendance_sessions s
        LEFT JOIN attendance_records r ON r.session_id = s.id
        GROUP BY s.id
        ORDER BY s.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # Convert date/time objects to strings
    for row in rows:
        if row.get("date"):
            row["date"] = str(row["date"])
        if row.get("session_time"):
            row["session_time"] = str(row["session_time"])
        if row.get("created_at"):
            row["created_at"] = str(row["created_at"])
    return rows


def get_session(session_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, subject_id, subject_name, lecture, date, session_time, created_at
        FROM attendance_sessions
        WHERE id = %s
    """, (session_id,))
    session = cur.fetchone()
    if session:
        if session.get("date"):
            session["date"] = str(session["date"])
        if session.get("session_time"):
            session["session_time"] = str(session["session_time"])
        if session.get("created_at"):
            session["created_at"] = str(session["created_at"])
    cur.close()
    conn.close()
    return session


def get_session_records(session_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT
            r.id,
            r.roll_no,
            st.name,
            r.status,
            r.confidence,
            r.manually_edited
        FROM attendance_records r
        LEFT JOIN students st ON st.roll_no = r.roll_no
        WHERE r.session_id = %s
        ORDER BY CAST(r.roll_no AS UNSIGNED)
    """, (session_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# --------------------------------------------------
# Attendance Records
# --------------------------------------------------

def save_attendance_records(session_id, records):
    """
    Insert or update attendance records for a session.
    records: list of {roll_no, status, confidence, manually_edited}
    """
    conn = get_connection()
    cur = conn.cursor()

    for rec in records:
        cur.execute("""
            INSERT INTO attendance_records
                (session_id, roll_no, status, confidence, manually_edited)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                confidence = VALUES(confidence),
                manually_edited = VALUES(manually_edited)
        """, (
            session_id,
            rec["roll_no"],
            rec["status"],
            rec.get("confidence"),
            1 if rec.get("manually_edited") else 0
        ))

    conn.commit()
    cur.close()
    conn.close()


# --------------------------------------------------
# Dashboard stats
# --------------------------------------------------

def get_dashboard_stats():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM attendance_sessions")
    total_sessions = cur.fetchone()["total"]

    # Today's session count
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM attendance_sessions
        WHERE DATE(created_at) = CURDATE()
    """)
    today_sessions = cur.fetchone()["total"]

    # Recent 5 sessions with stats
    cur.execute("""
        SELECT
            s.id,
            s.subject_name,
            s.lecture,
            s.date,
            s.session_time,
            SUM(CASE WHEN r.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            COUNT(r.id) AS total_count
        FROM attendance_sessions s
        LEFT JOIN attendance_records r ON r.session_id = s.id
        GROUP BY s.id
        ORDER BY s.created_at DESC
        LIMIT 5
    """)
    recent = cur.fetchall()
    for row in recent:
        if row.get("date"):
            row["date"] = str(row["date"])
        if row.get("session_time"):
            row["session_time"] = str(row["session_time"])

    cur.close()
    conn.close()

    return {
        "total_students": total_students,
        "total_sessions": total_sessions,
        "today_sessions": today_sessions,
        "recent_sessions": recent
    }
