import cv2
import os

DATASET = "CleanDataset"

DETECT_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNITION_MODEL = "models/face_recognition_sface_2021dec.onnx"

MIN_FACE_SIZE = 100
MIN_FACE_SCORE = 0.60
RECOGNITION_THRESHOLD = 0.363

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

    detector.setInputSize(
        (image.shape[1], image.shape[0])
    )

    _, faces = detector.detect(image)

    if faces is None:
        return []

    return faces

# --------------------------------------------------
# Select best face from an image
# --------------------------------------------------

def get_best_face(faces):

    if faces is None or len(faces) == 0:
        return None

    best_face = None
    best_area = 0

    for face in faces:

        x, y, w, h = face[:4]
        score = face[-1]

        if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
            continue

        if score < MIN_FACE_SCORE:
            continue

        area = w * h

        if area > best_area:
            best_area = area
            best_face = face

    return best_face

# --------------------------------------------------
# Generate face feature
# --------------------------------------------------

def get_feature(image, face):

    aligned = recognizer.alignCrop(
        image,
        face
    )

    feature = recognizer.feature(
        aligned
    )

    return feature

# --------------------------------------------------
# Build face database
# --------------------------------------------------

known_faces = {}

print("\nLoading student dataset...\n")

for roll_no in sorted(os.listdir(DATASET)):

    folder = os.path.join(
        DATASET,
        roll_no
    )

    if not os.path.isdir(folder):
        continue

    known_faces[roll_no] = []

    print("Student:", roll_no)

    valid_count = 0

    for filename in os.listdir(folder):

        path = os.path.join(
            folder,
            filename
        )

        image = cv2.imread(path)

        if image is None:
            print("  Skipped:", filename)
            continue

        faces = detect_faces(image)

        best_face = get_best_face(faces)

        if best_face is None:

            print(
                "  Skipped:",
                filename,
                "- no good face"
            )

            continue

        feature = get_feature(
            image,
            best_face
        )

        known_faces[roll_no].append(
            feature
        )

        valid_count += 1

    print(
        "  Valid images:",
        valid_count
    )
# Remove students for whom no valid features exist

known_faces = {
    roll_no: features
    for roll_no, features in known_faces.items()
    if len(features) > 0
}


print("\n--------------------------------")
print("Face database created")
print("--------------------------------")

for roll_no, features in known_faces.items():

    print(
        f"Roll {roll_no}: "
        f"{len(features)} face features"
    )

print("--------------------------------\n")

# --------------------------------------------------
# Start camera
# --------------------------------------------------

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("Could not open camera.")
    exit()


print("Camera started.")
print("Press Q to quit.\n")

# --------------------------------------------------
# Recognition loop
# --------------------------------------------------

while True:

    ret, frame = camera.read()

    if not ret:
        break

    faces = detect_faces(frame)

    for face in faces:

        x, y, w, h = face[:4].astype(int)

        # Ignore very small detections
        if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
            continue

        current_feature = get_feature(
            frame,
            face
        )

        best_roll = "Unknown"
        best_score = -1

        # ------------------------------------------
        # Compare against every student
        # ------------------------------------------

        for roll_no, features in known_faces.items():

            student_best_score = -1

            for known_feature in features:

                score = recognizer.match(
                    current_feature,
                    known_feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

                if score > student_best_score:
                    student_best_score = score

            # Keep best student match

            if student_best_score > best_score:

                best_score = student_best_score
                best_roll = roll_no

        # ------------------------------------------
        # Known / Unknown
        # ------------------------------------------

        if best_score >= RECOGNITION_THRESHOLD:

            color = (0, 255, 0)

            label = f"Roll No: {best_roll}"

        else:

            color = (0, 0, 255)

            label = "Unknown"
        # ------------------------------------------
        # Draw rectangle
        # ------------------------------------------

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            color,
            2
        )

        # ------------------------------------------
        # Draw label
        # ------------------------------------------

        cv2.putText(
            frame,
            label,
            (x, max(y - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

        # ------------------------------------------
        # Draw score
        # ------------------------------------------

        cv2.putText(
            frame,
            f"Score: {best_score:.2f}",
            (x, y + h + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )


    # ----------------------------------------------
    # Display camera
    # ----------------------------------------------

    cv2.imshow(
        "Face Recognition",
        frame
    )


    # Q = quit

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# --------------------------------------------------
# Release resources
# --------------------------------------------------

camera.release()
cv2.destroyAllWindows()