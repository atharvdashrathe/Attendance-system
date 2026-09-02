import cv2

MODEL = "models/face_detection_yunet_2023mar.onnx"

detector = cv2.FaceDetectorYN.create(
    MODEL,
    "",
    (320, 320),
    0.6,
    0.3,
    5000
)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Camera could not be opened.")
    exit()

print("Camera started. Press Q to quit.")

while True:

    ret, frame = camera.read()

    if not ret:
        print("Error: Could not read camera.")
        break

    # Set input size according to camera frame
    detector.setInputSize(
        (frame.shape[1], frame.shape[0])
    )

    # Detect faces
    _, faces = detector.detect(frame)

    if faces is not None:

        for face in faces:

            x, y, w, h = face[:4].astype(int)

            # Green rectangle around detected face
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            # Confidence
            confidence = face[-1]

            cv2.putText(
                frame,
                f"Face: {confidence:.2f}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    cv2.imshow("Face Detection", frame)

    # Press Q to exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()