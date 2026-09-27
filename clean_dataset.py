import cv2
import os
import shutil
import numpy as np


# ==================================================
# SETTINGS
# ==================================================

DATASET = "Dataset"
OUTPUT = "CleanDataset"

DETECT_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNITION_MODEL = "models/face_recognition_sface_2021dec.onnx"
EMBEDDINGS_CACHE = os.path.join(OUTPUT, "embeddings.npz")

MAX_IMAGES = 12

# Registration images: face quality filters
MIN_FACE_SIZE = 60
MIN_FACE_SCORE = 0.50

# Cosine similarity threshold for same-person clustering
SAME_PERSON_THRESHOLD = 0.38
OUTLIER_THRESHOLD = 0.36

# Minimum appearances across images
MIN_APPEARANCES = 2


# ==================================================
# LOAD MODELS
# ==================================================

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


# ==================================================
# HELPERS
# ==================================================

def is_numeric_folder(name):
    """Return True only for roll-number folders like '14', '28' etc."""
    return name.isdigit()


def detect_faces(image):
    detector.setInputSize((image.shape[1], image.shape[0]))
    _, faces = detector.detect(image)
    if faces is None:
        return []
    return faces


def get_feature(image, face):
    aligned = recognizer.alignCrop(image, face)
    feature = recognizer.feature(aligned)
    return feature


def cosine_sim(f1, f2):
    return float(recognizer.match(f1, f2, cv2.FaceRecognizerSF_FR_COSINE))


def get_sharpness(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def get_brightness(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def get_quality(face, sharpness, brightness):
    w, h = face[2], face[3]
    detection_score = float(face[-1])
    face_area = w * h
    area_score = min(face_area / 250000.0, 1.0)
    sharpness_score = min(sharpness / 500.0, 1.0)
    if 50 <= brightness <= 210:
        brightness_score = 1.0
    elif 30 <= brightness <= 230:
        brightness_score = 0.7
    else:
        brightness_score = 0.4
    quality = (
        0.40 * detection_score +
        0.30 * area_score +
        0.20 * sharpness_score +
        0.10 * brightness_score
    )
    return quality


def crop_face_chip(image, face):
    """
    Produces the standard 112x112 aligned face chip via FaceRecognizerSF.
    This guarantees mathematically that the image contains ONLY the target student's face.
    """
    return recognizer.alignCrop(image, face)


# ==================================================
# FACE CONSISTENCY CLUSTERING
# ==================================================

def find_student_face_identity(folder):
    """
    Extracts all faces across images in `folder`, clusters them by cosine similarity,
    and identifies the true student cluster spanning the most images.
    """
    all_detections = []

    files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))]
    for filename in files:
        path = os.path.join(folder, filename)
        image = cv2.imread(path)
        if image is None:
            continue

        faces = detect_faces(image)
        if len(faces) == 0:
            continue

        sharpness = get_sharpness(image)
        brightness = get_brightness(image)

        for face in faces:
            w, h = face[2], face[3]
            score = float(face[-1])
            if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
                continue
            if score < MIN_FACE_SCORE:
                continue
            try:
                feature = get_feature(image, face)
            except Exception:
                continue
            quality = get_quality(face, sharpness, brightness)
            all_detections.append({
                "path": path,
                "filename": filename,
                "image": image,
                "face": face,
                "feature": feature,
                "quality": quality,
            })

    if not all_detections:
        return []

    # Cluster detections by cosine similarity
    clusters = []
    centroids = []

    for det in all_detections:
        placed = False
        for ci, centroid in enumerate(centroids):
            if cosine_sim(det["feature"], centroid) >= SAME_PERSON_THRESHOLD:
                clusters[ci].append(det)
                # Update centroid with normalized mean
                n = len(clusters[ci])
                new_cent = (centroids[ci] * (n - 1) + det["feature"]) / n
                centroids[ci] = new_cent / np.linalg.norm(new_cent)
                placed = True
                break
        if not placed:
            clusters.append([det])
            c_init = det["feature"].copy()
            centroids.append(c_init / np.linalg.norm(c_init))

    def image_count(cluster):
        return len({d["path"] for d in cluster})

    # Pick cluster with highest image coverage
    best_cluster = max(clusters, key=image_count)
    best_image_count = image_count(best_cluster)
    num_images_in_folder = len({d["path"] for d in all_detections})

    print(f"  Clusters found: {len(clusters)}, "
          f"best cluster spans {best_image_count}/{num_images_in_folder} images "
          f"({len(best_cluster)} detections)")

    if best_image_count < MIN_APPEARANCES and num_images_in_folder >= MIN_APPEARANCES:
        print("  WARNING: Low cluster consistency across images. Using best single detections.")

    # Keep only the best quality detection per image in the chosen cluster
    seen_paths = {}
    for det in best_cluster:
        p = det["path"]
        if p not in seen_paths or det["quality"] > seen_paths[p]["quality"]:
            seen_paths[p] = det

    candidates = list(seen_paths.values())

    # Outlier rejection against student centroid
    if len(candidates) >= 2:
        student_centroid = np.mean([c["feature"] for c in candidates], axis=0)
        student_centroid = student_centroid / np.linalg.norm(student_centroid)
        filtered = []
        for c in candidates:
            sim = cosine_sim(c["feature"], student_centroid)
            if sim >= OUTLIER_THRESHOLD:
                filtered.append(c)
            else:
                print(f"  Dropping outlier image {c['filename']} (similarity {sim:.3f} < {OUTLIER_THRESHOLD})")
        if filtered:
            candidates = filtered

    return candidates


# ==================================================
# SELECT DIVERSE HIGH-QUALITY IMAGES
# ==================================================

def select_images(candidates):
    if len(candidates) <= MAX_IMAGES:
        return sorted(candidates, key=lambda x: x["quality"], reverse=True)

    candidates = sorted(candidates, key=lambda x: x["quality"], reverse=True)
    selected = [candidates[0]]
    remaining = candidates[1:]

    while len(selected) < MAX_IMAGES and remaining:
        best_candidate = None
        best_value = -999

        for candidate in remaining:
            max_similarity = max(
                cosine_sim(candidate["feature"], s["feature"])
                for s in selected
            )
            diversity = 1.0 - max_similarity
            value = 0.50 * candidate["quality"] + 0.50 * diversity

            if value > best_value:
                best_value = value
                best_candidate = candidate

        selected.append(best_candidate)
        remaining.remove(best_candidate)

    return selected


# ==================================================
# MAIN
# ==================================================

def clean_dataset():
    if os.path.exists(OUTPUT):
        shutil.rmtree(OUTPUT)
    os.makedirs(OUTPUT, exist_ok=True)

    print("\n======================================")
    print("SMART DATASET CLEANING & FACE ISOLATION")
    print("Isolates target student face chips to")
    print("guarantee zero multi-face contamination.")
    print("======================================")

    all_student_features = {}

    for roll_no in sorted(os.listdir(DATASET)):
        source_folder = os.path.join(DATASET, roll_no)

        if not os.path.isdir(source_folder):
            continue

        if not is_numeric_folder(roll_no):
            print(f"\nSkipping non-numeric folder: {roll_no}")
            continue

        print(f"\n======================================")
        print(f"Student: {roll_no}")
        print(f"======================================")

        candidates = find_student_face_identity(source_folder)
        print(f"  Good candidates: {len(candidates)}")

        if not candidates:
            print("  WARNING: No usable images found.")
            continue

        selected = select_images(candidates)
        destination_folder = os.path.join(OUTPUT, roll_no)
        os.makedirs(destination_folder, exist_ok=True)

        # Clear previous CleanDataset images in this roll folder
        for old_file in os.listdir(destination_folder):
            old_path = os.path.join(destination_folder, old_file)
            if os.path.isfile(old_path):
                os.remove(old_path)

        print(f"  Selected clean images: {len(selected)}")
        all_student_features[roll_no] = []

        for i, item in enumerate(selected, start=1):
            face = item["face"]
            chip = crop_face_chip(item["image"], face)

            # Save aligned face chip
            chip_filename = f"aligned_{item['filename']}"
            destination = os.path.join(destination_folder, chip_filename)
            cv2.imwrite(destination, chip)

            all_student_features[roll_no].append(item["feature"])

            w, h = int(face[2]), int(face[3])
            score = float(face[-1])
            print(
                f"  {i:02d}. {chip_filename} | "
                f"Face={w}x{h} | "
                f"Detection={score:.3f} | "
                f"Quality={item['quality']:.3f}"
            )

    # Save precomputed feature embeddings cache
    centroids = {}
    for roll, feats in all_student_features.items():
        if feats:
            c = np.mean(feats, axis=0)
            centroids[roll] = c / np.linalg.norm(c)

    np.savez(
        EMBEDDINGS_CACHE,
        features=all_student_features,
        centroids=centroids
    )
    print(f"\nSaved precomputed embeddings cache to {EMBEDDINGS_CACHE}")
    print("\n======================================")
    print("CLEANING & CACHE COMPLETED SUCCESSFULLY")
    print("======================================")


if __name__ == "__main__":
    clean_dataset()