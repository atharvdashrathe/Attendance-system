"""
recognize.py — High-Accuracy Face Recognition Module for Classroom Attendance
Supports multi-face classroom recognition, centroid + exemplar ensemble matching,
ambiguity margin filtering, and sub-millisecond cached feature loading.
"""

import cv2
import os
import sys
import numpy as np

# --------------------------------------------------
# Paths (relative to project root, i.e. AttendanceProject/)
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATASET = os.path.join(BASE_DIR, "CleanDataset")
EMBEDDINGS_CACHE = os.path.join(DATASET, "embeddings.npz")
DETECT_MODEL = os.path.join(BASE_DIR, "models", "face_detection_yunet_2023mar.onnx")
RECOGNITION_MODEL = os.path.join(BASE_DIR, "models", "face_recognition_sface_2021dec.onnx")

# --------------------------------------------------
# Configuration & Calibrated Thresholds
# --------------------------------------------------

# Standard threshold for portrait/registration quality faces
RECOGNITION_THRESHOLD = 0.363

# Calibrated classroom threshold for distance/angled faces with centroid matching
CLASSROOM_RECOGNITION_THRESHOLD = 0.340

# Ambiguity margin: difference required between top-1 and top-2 candidate
AMBIGUITY_MARGIN = 0.035
AMBIGUITY_SAFE_SCORE = 0.450

# Face detection parameters
MIN_FACE_SCORE = 0.55
CLASSROOM_MIN_FACE_SCORE = 0.40
CLASSROOM_MIN_FACE_SIZE = 28
CLASSROOM_DETECTION_MIN_SIDE = 1600
REGISTRATION_MIN_FACE_SIZE = 60

# --------------------------------------------------
# Load models (lazy — initialized once on first use)
# --------------------------------------------------

_detector = None
_recognizer = None
_known_faces = None       # {roll_no: [feature_array, ...]}
_known_centroids = None   # {roll_no: centroid_array}


def _is_numeric_folder(name):
    """Only load folders whose names are roll numbers (e.g. '19', '28')."""
    return name.isdigit()


def _get_detector():
    global _detector
    if _detector is None:
        _detector = cv2.FaceDetectorYN.create(
            DETECT_MODEL,
            "",
            (320, 320),
            CLASSROOM_MIN_FACE_SCORE,
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
# Core detection & Multi-scale Processing
# --------------------------------------------------

def detect_faces(image):
    """Detect all faces in an image at its current size."""
    detector = _get_detector()
    detector.setInputSize((image.shape[1], image.shape[0]))
    _, faces = detector.detect(image)
    if faces is None:
        return []
    return faces


def _iou(first, second):
    """Intersection-over-union for two bounding boxes [x, y, w, h]."""
    ax, ay, aw, ah = first[:4]
    bx, by, bw, bh = second[:4]
    left, top = max(ax, bx), max(ay, by)
    right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = aw * ah + bw * bh - intersection
    return float(intersection / union) if union > 0 else 0.0


def detect_classroom_faces(image):
    """
    Multi-scale face detection optimized for classroom photos.
    Runs detection on both native resolution and an upscaled pyramid
    layer for distant small faces, followed by Non-Maximum Suppression (NMS).
    """
    faces = list(detect_faces(image))
    height, width = image.shape[:2]
    shortest_side = min(height, width)

    if shortest_side < CLASSROOM_DETECTION_MIN_SIDE:
        scale = CLASSROOM_DETECTION_MIN_SIDE / float(shortest_side)
        enlarged = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )
        enlarged_faces = detect_faces(enlarged)
        for face in enlarged_faces:
            converted = face.copy()
            # YuNet landmarks & bbox coords are first 14 values; confidence is index 14
            converted[:14] /= scale
            faces.append(converted)

    # NMS to merge overlapping multi-scale detections
    merged = []
    for face in sorted(faces, key=lambda item: float(item[-1]), reverse=True):
        if not any(_iou(face, kept) >= 0.35 for kept in merged):
            merged.append(face)
    return merged


def get_best_face(faces, min_face_size=REGISTRATION_MIN_FACE_SIZE):
    """Returns the largest valid face from a list."""
    if faces is None or len(faces) == 0:
        return None

    best_face = None
    best_area = 0

    for face in faces:
        w, h = face[2], face[3]
        score = float(face[-1])

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
# Feature Extraction
# --------------------------------------------------

def get_feature(image, face=None):
    """
    Extracts 128-dim SFace feature embedding.
    If face is provided, performs rigid affine alignment (alignCrop) first.
    If face is None, assumes image is already an aligned 112x112 face crop.
    """
    recognizer = _get_recognizer()
    if face is not None:
        aligned = recognizer.alignCrop(image, face)
    else:
        # Check if already 112x112
        if image.shape[0] != 112 or image.shape[1] != 112:
            aligned = cv2.resize(image, (112, 112))
        else:
            aligned = image
    feature = recognizer.feature(aligned)
    return feature


def cosine_similarity(f1, f2):
    """Cosine similarity between two 128-dim embeddings."""
    recognizer = _get_recognizer()
    return float(recognizer.match(f1, f2, cv2.FaceRecognizerSF_FR_COSINE))


# --------------------------------------------------
# Load Known Faces (with Instant Cache Support)
# --------------------------------------------------

def load_known_faces(force_reload=False):
    """
    Loads SFace features and centroids for all registered students.
    Fast path loads precomputed embeddings in < 5ms.
    Fallback extracts features from CleanDataset images and rebuilds cache.
    Returns: dict {roll_no: [feature_array, ...]}
    """
    global _known_faces, _known_centroids

    if _known_faces is not None and not force_reload:
        return _known_faces

    # 1. Fast Path: Precomputed Embeddings Cache
    if os.path.exists(EMBEDDINGS_CACHE) and not force_reload:
        try:
            data = np.load(EMBEDDINGS_CACHE, allow_pickle=True)
            _known_faces = data["features"].item()
            if "centroids" in data:
                _known_centroids = data["centroids"].item()
            else:
                _known_centroids = {}
                for roll, feats in _known_faces.items():
                    if feats:
                        c = np.mean(feats, axis=0)
                        _known_centroids[roll] = c / np.linalg.norm(c)
            print(f"[recognize] Fast loaded {len(_known_faces)} students from embeddings cache.")
            return _known_faces
        except Exception as e:
            print(f"[recognize] Warning: Could not read embeddings cache ({e}), rebuilding from disk...")

    # 2. Fallback Path: Rebuild from CleanDataset
    print("\n[recognize] Loading student dataset from disk...")
    known = {}
    centroids = {}

    if not os.path.isdir(DATASET):
        print(f"[recognize] ERROR: CleanDataset not found at {DATASET}")
        _known_faces = {}
        _known_centroids = {}
        return _known_faces

    for roll_no in sorted(os.listdir(DATASET)):
        folder = os.path.join(DATASET, roll_no)
        if not os.path.isdir(folder) or not _is_numeric_folder(roll_no):
            continue

        known[roll_no] = []
        for filename in sorted(os.listdir(folder)):
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                continue
            path = os.path.join(folder, filename)
            image = cv2.imread(path)
            if image is None:
                continue

            # In CleanDataset, images are aligned face chips (112x112) or clean crops
            if image.shape[0] == 112 and image.shape[1] == 112:
                feature = get_feature(image)
            else:
                faces = detect_faces(image)
                best_face = get_best_face(faces, min_face_size=30)
                if best_face is None:
                    continue
                feature = get_feature(image, best_face)

            known[roll_no].append(feature)

        if known[roll_no]:
            c = np.mean(known[roll_no], axis=0)
            centroids[roll_no] = c / np.linalg.norm(c)
            print(f"[recognize] Roll {roll_no}: {len(known[roll_no])} clean features loaded")

    # Filter empty students
    known = {r: f for r, f in known.items() if len(f) > 0}
    _known_faces = known
    _known_centroids = centroids

    # Save cache for future instant startups
    try:
        np.savez(EMBEDDINGS_CACHE, features=known, centroids=centroids)
        print(f"[recognize] Saved embeddings cache to {EMBEDDINGS_CACHE}")
    except Exception as e:
        print(f"[recognize] Could not save cache: {e}")

    print(f"[recognize] Loaded {len(_known_faces)} students successfully.\n")
    return _known_faces


def get_known_centroids():
    """Returns dictionary of student roll_no -> normalized centroid embedding."""
    global _known_centroids
    if _known_centroids is None:
        load_known_faces()
    return _known_centroids


# --------------------------------------------------
# High-Accuracy Face Matching (Centroid + Exemplar Ensemble)
# --------------------------------------------------

def _match_face(feature, classroom_mode=False):
    """
    Match a query face feature vector against all known students using a
    Centroid + Top-K Exemplar ensemble score, with ambiguity margin checks.

    Returns:
        (roll_no, confidence_score) where roll_no is "UNKNOWN" if no student
        meets the calibrated threshold or if the match is ambiguous.
    """
    known = load_known_faces()
    centroids = get_known_centroids()

    if not known:
        return "UNKNOWN", 0.0

    threshold = CLASSROOM_RECOGNITION_THRESHOLD if classroom_mode else RECOGNITION_THRESHOLD

    candidate_scores = []

    for roll_no, features in known.items():
        # 1. Centroid Cosine Similarity
        centroid = centroids.get(roll_no)
        if centroid is not None:
            s_centroid = cosine_similarity(feature, centroid)
        else:
            s_centroid = -1.0

        # 2. Top Exemplar Cosine Similarity
        s_exemplars = [cosine_similarity(feature, f) for f in features]
        s_top = max(s_exemplars) if s_exemplars else -1.0

        # 3. Dual Ensemble Score: Weighted combination
        # 65% Centroid (high noise robustness) + 35% Best Exemplar (pose/expression flexibility)
        if s_centroid > -1.0:
            combined_score = 0.65 * s_centroid + 0.35 * s_top
        else:
            combined_score = s_top

        candidate_scores.append((roll_no, combined_score))

    # Rank candidates by combined score
    candidate_scores.sort(key=lambda x: x[1], reverse=True)

    top_roll, top_score = candidate_scores[0]

    # Ambiguity Check: if top-1 and top-2 are too close at borderline confidence
    if len(candidate_scores) > 1 and top_score < AMBIGUITY_SAFE_SCORE:
        second_roll, second_score = candidate_scores[1]
        score_diff = top_score - second_score
        if score_diff < AMBIGUITY_MARGIN:
            # Identity is ambiguous between two students, avoid false identification
            return "UNKNOWN", float(top_score)

    if top_score < threshold:
        return "UNKNOWN", float(top_score)

    return top_roll, float(top_score)


# --------------------------------------------------
# Main Recognition API
# --------------------------------------------------

def recognize_faces_in_image(image_bgr):
    """
    Process a classroom image and recognize all detected faces.

    Args:
        image_bgr: OpenCV BGR image (numpy array)

    Returns:
        List of dicts:
        [
            {
                "roll_no": "19",          # or "UNKNOWN"
                "confidence": 0.8542,
                "bbox": [x, y, w, h]
            },
            ...
        ]
    """
    faces = detect_classroom_faces(image_bgr)
    results = []

    for face in faces:
        x, y, w, h = face[:4].astype(int)
        score = float(face[-1])

        # Skip faces that are too small or low confidence for classroom
        if w < CLASSROOM_MIN_FACE_SIZE or h < CLASSROOM_MIN_FACE_SIZE:
            continue
        if score < CLASSROOM_MIN_FACE_SCORE:
            continue

        try:
            feature = get_feature(image_bgr, face)
            roll_no, confidence = _match_face(feature, classroom_mode=True)
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
# Convenience Helpers
# --------------------------------------------------

def get_registered_students():
    """Returns sorted list of all registered roll numbers."""
    known = load_known_faces()
    return sorted(known.keys())
