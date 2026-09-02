# 🎓 ClassTrack — Classroom Attendance System

> **AI-powered face recognition attendance tracker for classrooms.**
> Upload a classroom photo → get a fully-editable attendance sheet → export to Excel. All in seconds.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-green?logo=opencv)
![MySQL](https://img.shields.io/badge/MySQL-8.0%2B-orange?logo=mysql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 📸 How It Works

```
Upload 1–4 classroom photos
        ↓
YuNet detects every face
        ↓
SFace matches faces against the student dataset
        ↓
Attendance list generated (Present / Absent)
        ↓
Manually correct if needed → Finalize
        ↓
Saved to MySQL + exported to Excel
```

---

## ✨ Features

| Feature | Details |
|---|---|
| 🤖 **AI Face Recognition** | OpenCV YuNet detector + SFace recognizer (ONNX models) |
| 📷 **Multi-image Processing** | Upload up to 4 photos per session for better coverage |
| ✏️ **Manual Override** | Correct any misidentified student before finalizing |
| 📊 **Excel Export** | Auto-generates per-subject `.xlsx` attendance sheets |
| 🗂️ **Session History** | Browse, filter, and re-download any past session |
| 📈 **Dashboard** | Live stats — total students, sessions today, recent activity |
| 🧹 **Smart Dataset Cleaner** | Quality-score and diversity-based image selector for training data |
| 🌐 **Web UI** | Pure HTML/CSS/JS frontend, no framework needed |

---

## 🗂️ Project Structure

```
AttendanceProject/
├── backend/
│   ├── app.py          # Flask REST API (all endpoints)
│   ├── attendance.py   # Image processing & recognition pipeline
│   ├── database.py     # MySQL schema, queries & seeding
│   ├── excel.py        # Excel export logic (openpyxl)
│   └── recognize.py    # Face detection & SFace feature extraction
│
├── frontend/
│   ├── index.html      # Single-page app shell
│   ├── css/            # Stylesheets
│   └── js/
│       ├── app.js              # App initialization & routing
│       ├── dashboard.js        # Dashboard stats view
│       ├── take_attendance.js  # Upload & process photos
│       ├── preview.js          # Review & edit attendance results
│       ├── history.js          # Past sessions browser
│       ├── subjects.js         # Subject management
│       └── excel_downloads.js  # Excel file listing & download
│
├── models/
│   ├── face_detection_yunet_2023mar.onnx
│   └── face_recognition_sface_2021dec.onnx
│
├── Dataset/            # Raw student photos (input)
├── CleanDataset/       # Processed training images (output of cleaner)
├── excel_exports/      # Generated .xlsx attendance files
├── uploads/            # Temporary image uploads (auto-cleared)
│
├── clean_dataset.py    # Smart dataset preparation script
├── detect.py           # Standalone face detection test
├── recognize.py        # Standalone live camera recognition
├── run.py              # ✅ Main entry point
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python **3.8+**
- MySQL **8.0+** (running locally)
- Git

### 2. Clone the repository

```bash
git clone https://github.com/your-username/AttendanceProject.git
cd AttendanceProject
```

### 3. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure the database

Open `backend/database.py` and update the connection settings:

```python
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_PASSWORD",   # change this
    "database": "attendance_db"
}
```

> The database and all tables are created **automatically** on first run.

### 6. Add ONNX models

Download the pretrained models and place them in the `models/` folder:

| File | Source |
|---|---|
| `face_detection_yunet_2023mar.onnx` | [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) |
| `face_recognition_sface_2021dec.onnx` | [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) |

### 7. Prepare the student dataset

```
Dataset/
├── 101/          ← roll number as folder name
│   ├── photo1.jpg
│   └── photo2.jpg
├── 102/
│   └── photo1.jpg
...
```

Then run the smart dataset cleaner:

```bash
python clean_dataset.py
```

This selects up to **12 high-quality, diverse** face images per student and writes them to `CleanDataset/`.

### 8. Run the application

```bash
python run.py
```

Open your browser at **http://localhost:5000**

---

## 📡 API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard` | Summary stats & recent sessions |
| `GET` | `/api/students` | List all registered students |
| `GET` | `/api/subjects` | List all subjects |
| `POST` | `/api/subjects` | Add a new subject `{ "name": "..." }` |
| `DELETE` | `/api/subjects/<id>` | Remove a subject |
| `POST` | `/api/attendance/process` | Upload photos and run recognition |
| `POST` | `/api/attendance/finalize` | Save session to DB + export Excel |
| `GET` | `/api/sessions` | List all past sessions |
| `GET` | `/api/sessions/<id>` | Session details + attendance records |
| `GET` | `/api/sessions/<id>/excel` | Download Excel for a session |
| `GET` | `/api/excel/list` | List all exported Excel files |
| `GET` | `/api/excel/download/<filename>` | Download a specific Excel file |

---

## 🧠 Face Recognition Pipeline

```
Raw photo
   │
   ▼
YuNet Face Detection  (ONNX, confidence ≥ 0.60, min face 100×100 px)
   │
   ▼
Best face selected per image (largest area, highest confidence)
   │
   ▼
SFace feature extraction (128-dim embedding)
   │
   ▼
Cosine similarity match against CleanDataset embeddings
   │
   ▼
Threshold ≥ 0.363 → Present   |   Below threshold → Absent
```

### Dataset Cleaning Algorithm

`clean_dataset.py` scores each candidate image on:

| Criterion | Weight |
|---|---|
| Detection confidence | 40% |
| Face area | 30% |
| Sharpness (Laplacian variance) | 20% |
| Brightness (mean pixel value) | 10% |

If a student has more than 12 photos, a **greedy diversity selection** picks images that are both high-quality *and* visually diverse (low cosine similarity to already-selected images).

---

## 🗄️ Database Schema

```sql
subjects            — id, name (UNIQUE)
students            — id, roll_no (UNIQUE), name
attendance_sessions — id, subject_id, subject_name, lecture, date, session_time, created_at
attendance_records  — id, session_id, roll_no, status (Present/Absent), confidence, manually_edited
```

Students are **auto-seeded** from `CleanDataset/` folder names (roll numbers) on startup.

---

## 🛠️ Utility Scripts

| Script | Purpose |
|---|---|
| `clean_dataset.py` | Prepare and clean the training image dataset |
| `detect.py` | Test face detection on a single image |
| `recognize.py` | Live webcam face recognition demo |
| `run.py` | **Main entry point** — starts the full server |

---

## ⚙️ Configuration

Key constants you can tune in the source files:

| Constant | File | Default | Description |
|---|---|---|---|
| `MIN_FACE_SIZE` | `recognize.py` | `100` | Minimum face width/height in px |
| `MIN_FACE_SCORE` | `recognize.py` | `0.60` | Minimum detection confidence |
| `RECOGNITION_THRESHOLD` | `recognize.py` | `0.363` | Cosine similarity cutoff for a match |
| `MAX_IMAGES` | `clean_dataset.py` | `12` | Max images per student in CleanDataset |
| `MAX_CONTENT_LENGTH` | `app.py` | `50 MB` | Maximum upload size |

---

## 📦 Dependencies

```
opencv-python >= 4.8.0
numpy         >= 1.24.0
flask         >= 3.0.0
flask-cors    >= 4.0.0
mysql-connector-python >= 8.0.0
openpyxl      >= 3.1.0
```

Install all with:

```bash
pip install -r requirements.txt
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [OpenCV](https://opencv.org/) — Computer vision library
- [OpenCV Zoo](https://github.com/opencv/opencv_zoo) — Pretrained ONNX models (YuNet, SFace)
- [Flask](https://flask.palletsprojects.com/) — Lightweight Python web framework
- [openpyxl](https://openpyxl.readthedocs.io/) — Excel file generation
