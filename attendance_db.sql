-- ============================================================
-- attendance_db.sql
-- MySQL schema for the Face-Recognition Attendance System
--
-- Usage:
--   mysql -u root -p < attendance_db.sql
--
-- Tables:
--   subjects              -- manageable subject list
--   students              -- registered students
--   attendance_sessions   -- one record per attendance session
--   attendance_records    -- one record per student per session
-- ============================================================

-- Create and select the database
CREATE DATABASE IF NOT EXISTS attendance_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE attendance_db;

-- ------------------------------------------------------------
-- 1. subjects
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    id   INT          AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- ------------------------------------------------------------
-- 2. students
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id      INT          AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(20)  NOT NULL UNIQUE,
    name    VARCHAR(100) NOT NULL
);

-- ------------------------------------------------------------
-- 3. attendance_sessions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id           INT          AUTO_INCREMENT PRIMARY KEY,
    subject_id   INT          NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    lecture      VARCHAR(100) NOT NULL,
    date         DATE         NOT NULL,
    session_time TIME         NOT NULL,
    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_session_subject
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- ------------------------------------------------------------
-- 4. attendance_records
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance_records (
    id              INT                       AUTO_INCREMENT PRIMARY KEY,
    session_id      INT                       NOT NULL,
    roll_no         VARCHAR(20)               NOT NULL,
    status          ENUM('Present', 'Absent') NOT NULL,
    confidence      FLOAT                     DEFAULT NULL,
    manually_edited TINYINT(1)                DEFAULT 0,

    UNIQUE KEY uq_session_student (session_id, roll_no),

    CONSTRAINT fk_record_session
        FOREIGN KEY (session_id) REFERENCES attendance_sessions(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ============================================================
-- Sample seed data (optional -- remove if not needed)
-- ============================================================

-- Sample subjects
INSERT IGNORE INTO subjects (name) VALUES
    ('Data Structures'),
    ('Machine Learning'),
    ('DTI');

-- Sample students (roll numbers match the Dataset/ folders)
INSERT IGNORE INTO students (roll_no, name) VALUES
    ('abc', 'Student abc'),
    ('bcd', 'Student bcd'),
    ('xyz', 'Student xyz'),
    ('34',  'Student 34'),
    ('36',  'Student 36'),
    ('37',  'Student 37'),
    ('38',  'Student 38');
