"""
attendance.py — Multi-image classroom attendance processor

Accepts multiple uploaded image paths, runs recognition on each,
deduplicates roll numbers across images, and generates the final
Present/Absent list for all registered students.
"""

import cv2
import os

from recognize import recognize_faces_in_image, get_registered_students


def process_images(image_paths):
    """
    Process 2–4 classroom images and produce attendance results.

    Args:
        image_paths: list of absolute file paths to classroom images

    Returns:
        {
            "records": [
                {
                    "roll_no": "14",
                    "status": "Present",        # or "Absent"
                    "confidence": 0.82,         # best confidence seen; None if Absent
                    "source_images": [0, 2],    # indices of images where found
                },
                ...
            ],
            "image_results": [                  # per-image face detections
                [
                    {"roll_no": "14", "confidence": 0.82, "bbox": [x,y,w,h]},
                    ...
                ],
                ...
            ],
            "registered_students": ["14", "28", ...]
        }
    """

    registered = get_registered_students()

    # Track best confidence per student across all images
    # {roll_no: {"confidence": float, "source_images": [int]}}
    seen_students = {}

    image_results = []

    for idx, image_path in enumerate(image_paths):
        image = cv2.imread(image_path)

        if image is None:
            print(f"[attendance] Could not read image: {image_path}")
            image_results.append([])
            continue

        faces = recognize_faces_in_image(image)
        image_results.append(faces)

        for face in faces:
            roll_no = face["roll_no"]
            confidence = face["confidence"]

            if roll_no == "UNKNOWN":
                continue

            if roll_no not in seen_students:
                seen_students[roll_no] = {
                    "confidence": confidence,
                    "source_images": [idx]
                }
            else:
                # Keep best confidence
                if confidence > seen_students[roll_no]["confidence"]:
                    seen_students[roll_no]["confidence"] = confidence
                if idx not in seen_students[roll_no]["source_images"]:
                    seen_students[roll_no]["source_images"].append(idx)

    # Build final attendance records for ALL registered students
    records = []

    for roll_no in registered:
        if roll_no in seen_students:
            records.append({
                "roll_no": roll_no,
                "status": "Present",
                "confidence": round(seen_students[roll_no]["confidence"], 4),
                "source_images": seen_students[roll_no]["source_images"]
            })
        else:
            records.append({
                "roll_no": roll_no,
                "status": "Absent",
                "confidence": None,
                "source_images": []
            })

    return {
        "records": records,
        "image_results": image_results,
        "registered_students": registered
    }
