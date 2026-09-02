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

MAX_IMAGES = 12

MIN_FACE_SIZE = 100
MIN_FACE_SCORE = 0.60


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
# FACE DETECTION
# ==================================================

def detect_faces(image):

    detector.setInputSize(
        (image.shape[1], image.shape[0])
    )

    _, faces = detector.detect(image)

    if faces is None:
        return []

    return faces


# ==================================================
# SELECT LARGEST GOOD FACE
# ==================================================

def get_best_face(faces):

    if faces is None or len(faces) == 0:
        return None

    best_face = None
    best_area = 0

    for face in faces:

        x, y, w, h = face[:4]

        score = face[-1]

        if w < MIN_FACE_SIZE:
            continue

        if h < MIN_FACE_SIZE:
            continue

        if score < MIN_FACE_SCORE:
            continue

        area = w * h

        if area > best_area:

            best_area = area
            best_face = face

    return best_face


# ==================================================
# SFACE FEATURE
# ==================================================

def get_feature(image, face):

    aligned = recognizer.alignCrop(
        image,
        face
    )

    feature = recognizer.feature(
        aligned
    )

    return feature


# ==================================================
# SHARPNESS
# ==================================================

def get_sharpness(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()


# ==================================================
# BRIGHTNESS
# ==================================================

def get_brightness(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return float(np.mean(gray))


# ==================================================
# QUALITY SCORE
# ==================================================

def get_quality(face, sharpness, brightness):

    x, y, w, h = face[:4]

    detection_score = float(face[-1])

    face_area = w * h

    # Face size score
    area_score = min(
        face_area / 250000.0,
        1.0
    )

    # Sharpness score
    # IMPORTANT:
    # This is now a ranking factor,
    # NOT a rejection condition.

    sharpness_score = min(
        sharpness / 500.0,
        1.0
    )

    # Brightness score
    if 50 <= brightness <= 210:

        brightness_score = 1.0

    elif 30 <= brightness <= 230:

        brightness_score = 0.7

    else:

        brightness_score = 0.4

    # Final quality
    quality = (
        0.40 * detection_score +
        0.30 * area_score +
        0.20 * sharpness_score +
        0.10 * brightness_score
    )

    return quality


# ==================================================
# SIMILARITY
# ==================================================

def similarity(feature1, feature2):

    return recognizer.match(
        feature1,
        feature2,
        cv2.FaceRecognizerSF_FR_COSINE
    )


# ==================================================
# COLLECT GOOD CANDIDATES
# ==================================================

def collect_candidates(folder):

    candidates = []

    for filename in os.listdir(folder):

        path = os.path.join(
            folder,
            filename
        )

        image = cv2.imread(path)

        if image is None:

            print(
                filename,
                "-> rejected: invalid image"
            )

            continue

        faces = detect_faces(image)

        face = get_best_face(faces)

        if face is None:

            print(
                filename,
                "-> rejected: no good face"
            )

            continue

        # ------------------------------------------------
        # DO NOT reject based on sharpness
        # ------------------------------------------------

        sharpness = get_sharpness(image)

        brightness = get_brightness(image)

        feature = get_feature(
            image,
            face
        )

        quality = get_quality(
            face,
            sharpness,
            brightness
        )

        candidates.append({
            "filename": filename,
            "path": path,
            "feature": feature,
            "quality": quality,
            "sharpness": sharpness,
            "brightness": brightness,
            "face": face
        })

        print(
            filename,
            f"-> candidate | "
            f"Sharpness={sharpness:.1f} | "
            f"Quality={quality:.3f}"
        )

    return candidates


# ==================================================
# SELECT DIVERSE HIGH-QUALITY IMAGES
# ==================================================

def select_images(candidates):

    if len(candidates) <= MAX_IMAGES:

        return sorted(
            candidates,
            key=lambda x: x["quality"],
            reverse=True
        )

    # Start with highest quality image

    candidates = sorted(
        candidates,
        key=lambda x: x["quality"],
        reverse=True
    )

    selected = [
        candidates[0]
    ]

    remaining = candidates[1:]

    while len(selected) < MAX_IMAGES and remaining:

        best_candidate = None
        best_value = -999

        for candidate in remaining:

            # Similarity to selected images

            max_similarity = max(
                similarity(
                    candidate["feature"],
                    selected_item["feature"]
                )
                for selected_item in selected
            )

            # Diversity
            diversity = 1.0 - max_similarity

            # Quality + diversity

            value = (
                0.50 * candidate["quality"] +
                0.50 * diversity
            )

            if value > best_value:

                best_value = value
                best_candidate = candidate

        selected.append(
            best_candidate
        )

        remaining.remove(
            best_candidate
        )

    return selected


# ==================================================
# MAIN
# ==================================================

os.makedirs(
    OUTPUT,
    exist_ok=True
)


print("\n======================================")
print("SMART DATASET CLEANING")
print("======================================")


for roll_no in sorted(os.listdir(DATASET)):

    source_folder = os.path.join(
        DATASET,
        roll_no
    )

    if not os.path.isdir(source_folder):
        continue

    print("\n======================================")
    print("Student:", roll_no)
    print("======================================")

    candidates = collect_candidates(
        source_folder
    )

    print(
        "\nGood candidates:",
        len(candidates)
    )

    if len(candidates) == 0:

        print(
            "WARNING: No usable images found."
        )

        continue

    selected = select_images(
        candidates
    )

    destination_folder = os.path.join(
        OUTPUT,
        roll_no
    )

    os.makedirs(
        destination_folder,
        exist_ok=True
    )

    # Remove previous CleanDataset images

    for old_file in os.listdir(
        destination_folder
    ):

        old_path = os.path.join(
            destination_folder,
            old_file
        )

        if os.path.isfile(old_path):

            os.remove(old_path)

    print(
        "\nSelected images:",
        len(selected)
    )

    for i, item in enumerate(
        selected,
        start=1
    ):

        destination = os.path.join(
            destination_folder,
            item["filename"]
        )

        shutil.copy2(
            item["path"],
            destination
        )

        face = item["face"]

        x, y, w, h = face[:4].astype(int)

        score = float(face[-1])

        print(
            f"{i:02d}. "
            f"{item['filename']} | "
            f"Face={w}x{h} | "
            f"Detection={score:.3f} | "
            f"Sharpness={item['sharpness']:.1f} | "
            f"Quality={item['quality']:.3f}"
        )


print("\n======================================")
print("CLEANING COMPLETED")
print("======================================")

print(
    "Original Dataset was NOT modified."
)

print(
    "Selected images are in:",
    OUTPUT
)