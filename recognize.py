"""
recognize.py — Real-time Webcam Face Recognition with Ensemble Matching
Uses precomputed embeddings cache, centroid + exemplar matching, and ambiguity filtering.
"""

import cv2
import os
import sys
import numpy as np

DATASET = "CleanDataset"
EMBEDDINGS_CACHE = os.path.join(DATASET, "embeddings.npz")
DETECT_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNITION_MODEL = "models/face_recognition_sface_2021dec.onnx"

MIN_FACE_SIZE = 50
MIN_FACE_SCORE = 0.60
RECOGNITION_THRESHOLD = 0.363
AMBIGUITY_MARGIN = 0.035
AMBIGUITY_SAFE_SCORE = 0.450

# --------------------------------------------------
# Load models
# --------------------------------------------------

detector = cv2.FaceDetectorYN.create(
    DETECT_MODEL,
    "",
    (320, 320),
    MIN_FACE_SCORE,
    0.3,
    5000
)

recognizer = cv2.FaceRecognizerSF.create(
    RECOGNITION_MODEL,
    ""
)

# --------------------------------------------------
# Detect faces
# --------------------------------------------------

def detect_faces(image):
    detector.setInputSize((image.shape[1], image.shape[0]))
    _, faces = detector.detect(image)
    if faces is None:
        return []
    return faces


def get_feature(image, face=None):
    if face is not None:
        aligned = recognizer.alignCrop(image, face)
    else:
        if image.shape[0] != 112 or image.shape[1] != 112:
            aligned = cv2.resize(image, (112, 112))
        else:
            aligned = image
    return recognizer.feature(aligned)


def cosine_similarity(f1, f2):
    return float(recognizer.match(f1, f2, cv2.FaceRecognizerSF_FR_COSINE))


# --------------------------------------------------
# Build face database (with instant cache support)
# --------------------------------------------------

known_faces = {}
known_centroids = {}

if os.path.exists(EMBEDDINGS_CACHE):
    print("[recognize] Loading fast precomputed embeddings...")
    data = np.load(EMBEDDINGS_CACHE, allow_pickle=True)
    known_faces = data["features"].item()
    if "centroids" in data:
        known_centroids = data["centroids"].item()
    else:
        for roll, feats in known_faces.items():
            if feats:
                c = np.mean(feats, axis=0)
                known_centroids[roll] = c / np.linalg.norm(c)
else:
    print("\nLoading student dataset from disk...\n")
    for roll_no in sorted(os.listdir(DATASET)):
        folder = os.path.join(DATASET, roll_no)
        if not os.path.isdir(folder) or not roll_no.isdigit():
            continue

        known_faces[roll_no] = []
        for filename in sorted(os.listdir(folder)):
            path = os.path.join(folder, filename)
            image = cv2.imread(path)
            if image is None:
                continue

            if image.shape[0] == 112 and image.shape[1] == 112:
                feat = get_feature(image)
            else:
                faces = detect_faces(image)
                if not faces:
                    continue
                best_face = max(faces, key=lambda f: f[2]*f[3])
                feat = get_feature(image, best_face)

            known_faces[roll_no].append(feat)

        if known_faces[roll_no]:
            c = np.mean(known_faces[roll_no], axis=0)
            known_centroids[roll_no] = c / np.linalg.norm(c)

    known_faces = {r: f for r, f in known_faces.items() if len(f) > 0}

print("\n--------------------------------")
print(f"Face database loaded ({len(known_faces)} students)")
print("--------------------------------\n")


def match_face(feature):
    candidate_scores = []
    for roll_no, features in known_faces.items():
        centroid = known_centroids.get(roll_no)
        s_centroid = cosine_similarity(feature, centroid) if centroid is not None else -1.0
        s_exemplars = [cosine_similarity(feature, f) for f in features]
        s_top = max(s_exemplars) if s_exemplars else -1.0

        combined = 0.65 * s_centroid + 0.35 * s_top if s_centroid > -1.0 else s_top
        candidate_scores.append((roll_no, combined))

    if not candidate_scores:
        return "Unknown", 0.0

    candidate_scores.sort(key=lambda x: x[1], reverse=True)
    top_roll, top_score = candidate_scores[0]

    if len(candidate_scores) > 1 and top_score < AMBIGUITY_SAFE_SCORE:
        second_score = candidate_scores[1][1]
        if top_score - second_score < AMBIGUITY_MARGIN:
            return "Unknown", top_score

    if top_score < RECOGNITION_THRESHOLD:
        return "Unknown", top_score

    return top_roll, top_score


# --------------------------------------------------
# Start camera & recognition loop
# --------------------------------------------------

if __name__ == "__main__":
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Could not open camera.")
        sys.exit(1)

    print("Camera started. Press Q to quit.\n")

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        faces = detect_faces(frame)

        for face in faces:
            x, y, w, h = face[:4].astype(int)

            if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                continue

            current_feature = get_feature(frame, face)
            best_roll, best_score = match_face(current_feature)

            if best_roll != "Unknown":
                color = (0, 255, 0)
                label = f"Roll No: {best_roll}"
            else:
                color = (0, 0, 255)
                label = "Unknown"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, max(y - 10, 25)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(frame, f"Score: {best_score:.2f}", (x, y + h + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()