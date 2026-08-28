# AI-Based CCTV Attendance Management System

## Current platform boundary
This repository currently contains a working Flask attendance application and a separate Vite/React workspace. The Flask application remains the system of record for authentication, student registration, face capture/recognition, attendance, dashboards, and Excel export. Camera configuration is now persisted server-side in SQLite and exposed through authenticated camera management and diagnostic endpoints.

The industrial safety platform is being upgraded incrementally. Detection, alert, incident, reporting, and role modules should be added behind these existing boundaries rather than replacing the attendance workflow.

### Camera API contract
- `GET /api/cameras` returns camera metadata without stream URLs or credentials.
- `POST /api/cameras` accepts `name`, `camera_type`, `stream_url`, `location`, and `department`.
- `POST /api/cameras/test` validates a webcam index or `rtsp://`, `http://`, or `https://` stream and attempts to receive a frame.
- `POST /api/cameras/<id>/test` records the latest connection status and diagnostic error.
- `DELETE /api/cameras/<id>` removes a saved configuration.

Mobile camera apps use different endpoints; enter the exact URL supplied by the app, such as `http://PHONE_IP:PORT/video`, rather than relying on a hard-coded path.

## Abstract
This project is a final-year engineering solution that uses a camera stream to detect and recognize students in real time, and automatically mark attendance. It is designed for demonstration in a classroom environment using a local webcam or RTSP CCTV source.

## Problem Statement
Manual attendance tracking is time-consuming, error-prone, and difficult to scale across large student groups. A CCTV-based AI recognition system automates attendance with a timestamped record and reduces administrative effort.

## Objectives
- Use a webcam or CCTV feed as the input source
- Detect and recognize students automatically
- Prevent duplicate attendance on a single date
- Record attendance with confidence and camera metadata
- Provide faculty dashboard features and export functionality

## Features
- Admin login with hashed password
- Student registration and dataset capture
- Face detection and embedding storage
- Live camera feed with overlays
- Automatic attendance marking
- Dashboard with attendance summary
- Search and filter attendance records
- CSV and Excel export
- SQLite database

## Technology Stack
- Python
- Flask
- SQLite
- OpenCV
- NumPy
- Pandas
- Pillow
- OpenPyXL

## Project Structure
```text
AI_CCTV_Attendance/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── database/
│   └── db.py
├── recognition/
│   ├── face_detection.py
│   ├── face_recognition.py
│   └── attendance.py
├── dataset/
├── encodings/
│   └── face_encodings.pkl
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── dashboard.js
│   └── captured/
├── templates/
│   ├── login.html
│   ├── dashboard.html
│   ├── students.html
│   ├── register_student.html
│   ├── live_camera.html
│   ├── attendance.html
│   └── reports.html
└── attendance.db
```

## Installation

### 1. Create virtual environment
```bash
cd AI_CCTV_Attendance
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
python app.py
```

Open the browser at http://localhost:5000/login

## Default Login
- Username: admin
- Password: admin123

## Configuration
The app reads settings from `config.py` and environment variables such as:
- `SECRET_KEY`
- `DATABASE_PATH`
- `CAMERA_SOURCE`
- `CAMERA_ID`
- `RECOGNITION_THRESHOLD`
- `REQUIRED_CONFIRMATION_FRAMES`
- `ATTENDANCE_START_TIME`
- `LATE_AFTER`

## Webcam Setup
Set the camera source to `0` for laptop webcam or set `CAMERA_SOURCE` to an RTSP URL.

## Security and Privacy
- Passwords are stored as hashes
- Face embeddings are not exposed publicly
- Access to admin pages is protected by login
- Uploads are validated before use
- Only minimal biometric data needed for recognition is stored

## Troubleshooting
- If OpenCV cannot open the camera, check the camera source and permissions.
- If recognition confidence is poor, capture clearer and front-facing images.
- If no face is detected, ensure proper lighting and image quality.
- If the app fails to start, install dependencies again and check Python version compatibility.

## Future Enhancements
- Multi-camera support
- Liveness detection
- Mask and occlusion detection
- Bulk student import
- Cloud analytics
- SMS/email notifications

## Notes
This project uses a lightweight OpenCV-based embedding approach that is simple to run on a local machine and easy to extend. For a production-grade system, the recognition module can be upgraded to FaceNet or ArcFace models for higher accuracy.
