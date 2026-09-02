"""
recognize.py — Importable face recognition module
Extracted from the original webcam-based recognize.py.

Key differences:
- No webcam loop, no cv2.imshow
- Processes ALL valid detected faces (not just the largest) — classroom mode
- Returns structured results per face
- Safe to import from other modules
"""

import cv2
import os
import sys

# --------------------------------------------------
# Paths (relative to project root, i.e. AttendanceProject/)
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATASET = os.path.join(BASE_DIR, "CleanDataset")
DETECT_MODEL = os.path.join(BASE_DIR, "models", "face_detection_yunet_2023mar.onnx")
RECOGNITION_MODEL = os.path.join(BASE_DIR, "models", "face_recognition_sface_2021dec.onnx")

# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Registration threshold (unchanged from original)
RECOGNITION_THRESHOLD = 0.363

# Detection confidence threshold (unchanged from original)
MIN_FACE_SCORE = 0.60

# For CLASSROOM images: smaller than registration (100) to catch farther faces
CLASSROOM_MIN_FACE_SIZE = 60

# For REGISTRATION images: keep original value
REGISTRATION_MIN_FACE_SIZE = 100

# --------------------------------------------------
# Load models (lazy — done once on first use)
# --------------------------------------------------

_detector = None
_recognizer = None
_known_faces = None   # {roll_no: [feature, ...]}


def _get_detector():
    global _detector
    if _detector is None:
        _detector = cv2.FaceDetectorYN.create(
            DETECT_MODEL,
            "",
            (320, 320),
            MIN_FACE_SCORE,
            0.3,
            5000
        )
    return _detector


def _get_recognizer():
    global _recognizer
    if _recognizer is None:
        _recognizer = cv2.FaceRecognizerSF.create(
            RECOGNITION_MODEL,
            ""
        )
    return _recognizer


# --------------------------------------------------
# Core detection
# --------------------------------------------------

def detect_faces(image):
    """Detect all faces in an image. Returns list of face arrays."""
    detector = _get_detector()
    detector.setInputSize((image.shape[1], image.shape[0]))
    _, faces = detector.detect(image)
    if faces is None:
        return []
    return faces


# --------------------------------------------------
# Get best (largest valid) face — used for registration images
# --------------------------------------------------

def get_best_face(faces, min_face_size=REGISTRATION_MIN_FACE_SIZE):
    """
    Returns the largest valid face from a list.
    Used for registration images (one student per photo).
    """
    if faces is None or len(faces) == 0:
        return None

    best_face = None
    best_area = 0

    for face in faces:
        x, y, w, h = face[:4]
        score = face[-1]

        if w < min_face_size or h < min_face_size:
            continue
        if score < MIN_FACE_SCORE:
            continue

        area = w * h
        if area > best_area:
            best_area = area
            best_face = face

    return best_face


# --------------------------------------------------
# Get feature vector for a face
# --------------------------------------------------

def get_feature(image, face):
    recognizer = _get_recognizer()
    aligned = recognizer.alignCrop(image, face)
    feature = recognizer.feature(aligned)
    return feature


# --------------------------------------------------
# Load known faces from CleanDataset
# --------------------------------------------------

def load_known_faces(force_reload=False):
    """
    Load SFace features for all students in CleanDataset.
    Results are cached in _known_faces; call with force_reload=True to refresh.
    Returns: {roll_no: [feature, ...]}
    """
    global _known_faces

    if _known_faces is not None and not force_reload:
        return _known_faces

    print("\n[recognize] Loading student dataset...")

    known = {}

    if not os.path.isdir(DATASET):
        print(f"[recognize] ERROR: CleanDataset not found at {DATASET}")
        _known_faces = {}
        return _known_faces

    for roll_no in sorted(os.listdir(DATASET)):
        folder = os.path.join(DATASET, roll_no)

        if not os.path.isdir(folder):
            continue

        known[roll_no] = []
        valid_count = 0

        for filename in os.listdir(folder):
            path = os.path.join(folder, filename)
            image = cv2.imread(path)

            if image is None:
                continue

            faces = detect_faces(image)
            best_face = get_best_face(faces, min_face_size=REGISTRATION_MIN_FACE_SIZE)

            if best_face is None:
                continue

            feature = get_feature(image, best_face)
            known[roll_no].append(feature)
            valid_count += 1

        print(f"[recognize] Roll {roll_no}: {valid_count} valid face features")

    # Remove students with no valid features
    known = {r: f for r, f in known.items() if len(f) > 0}

    print(f"[recognize] Loaded {len(known)} students\n")
    _known_faces = known
    return _known_faces


# --------------------------------------------------
# Recognize a single face feature against known faces
# --------------------------------------------------

def _match_face(feature):
    """
    Match a feature vector against all known students.
    Returns (roll_no, score) or ("UNKNOWN", score).
    """
    known = load_known_faces()
    recognizer = _get_recognizer()

    best_roll = "UNKNOWN"
    best_score = -1.0

    for roll_no, features in known.items():
        student_best = -1.0

        for known_feature in features:
            score = recognizer.match(
                feature,
                known_feature,
                cv2.FaceRecognizerSF_FR_COSINE
            )
            if score > student_best:
                student_best = score

        if student_best > best_score:
            best_score = student_best
            best_roll = roll_no

    if best_score < RECOGNITION_THRESHOLD:
        return "UNKNOWN", float(best_score)

    return best_roll, float(best_score)


# --------------------------------------------------
# Main API: recognize ALL faces in a classroom image
# --------------------------------------------------

def recognize_faces_in_image(image_bgr):
    """
    Process a classroom image and recognize all valid faces.

    Args:
        image_bgr: OpenCV BGR image (numpy array)

    Returns:
        List of dicts:
        [
            {
                "roll_no": "14",          # or "UNKNOWN"
                "confidence": 0.82,
                "bbox": [x, y, w, h]
            },
            ...
        ]
    """
    faces = detect_faces(image_bgr)
    results = []

    for face in faces:
        x, y, w, h = face[:4].astype(int)
        score = float(face[-1])

        # Skip faces that are too small or low confidence for classroom
        if w < CLASSROOM_MIN_FACE_SIZE or h < CLASSROOM_MIN_FACE_SIZE:
            continue
        if score < MIN_FACE_SCORE:
            continue

        try:
            feature = get_feature(image_bgr, face)
            roll_no, confidence = _match_face(feature)
        except Exception as e:
            print(f"[recognize] Error processing face at ({x},{y}): {e}")
            continue

        results.append({
            "roll_no": roll_no,
            "confidence": round(confidence, 4),
            "bbox": [x, y, w, h]
        })

    return results


# --------------------------------------------------
# Convenience: get all registered roll numbers
# --------------------------------------------------

def get_registered_students():
    """Returns sorted list of all registered roll numbers."""
    known = load_known_faces()
    return sorted(known.keys())
