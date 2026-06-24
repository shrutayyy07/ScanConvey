# ScanConvey - Smart Conveyor Belt Detection System

Advanced object detection, tracking, and counting system for conveyor belts with belt-region constraint, OTP authentication, and video logging.

## 🚀 What's New (v4.0.0)

✅ **ScanConvey Branding** - Fresh UI with cyan/blue gradient and integrated logo  
✅ **Conveyor Belt Region Detection** - Only counts objects ON the belt (not background clutter)  
✅ **OTP Authentication** - Phone/email based login with 6-digit OTP  
✅ **Video Processing Logs** - Automatic logging of all processed videos with category-wise counts  
✅ **Session Management** - Persistent sessions stored in SQLite  
✅ **User History** - View all past video processing results  

## 🏗️ Architecture

```
┌─────────────────┐
│ React Frontend  │ (Vite + TypeScript + Tailwind)
│  - Login Portal │
│  - Video Upload │
│  - Live Stream  │
│  - History Logs │
└────────┬────────┘
         │
┌────────▼────────────────────────┐
│  FastAPI Backend (Python)        │
│  - OTP Auth                      │
│  - Belt Region Detection         │
│  - MOG2 + YOLOv8                 │
│  - Centroid Tracking             │
│  - SQLite Logging                │
└────────┬────────────────────────┘
         │
┌────────▼─────────────────────┐
│ Optional: Java Service (gRPC) │
│ - Rule Engine                 │
│ - Audit Logging               │
└───────────────────────────────┘
```

## 📋 Prerequisites

- **Python 3.9+**
- **Node.js 16+** (for frontend)
- **ffmpeg** (for video processing)
- **OpenCV, YOLOv8, FastAPI** (installed via pip)

## 🏠 Local Setup

### 1️⃣ **Backend Setup**

```bash
cd scanconvey/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend on http://localhost:8000
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 2️⃣ **Frontend Setup**

```bash
cd scanconvey/frontend

# Install dependencies
npm install

# Create .env file
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
EOF

# Run dev server on http://localhost:5173
npm run dev
```

**Expected Output:**
```
  ➜  Local:   http://127.0.0.1:5173/
  ➜  press h to show help
```

### 3️⃣ **Access the Application**

Open your browser and navigate to:
```
http://localhost:5173
```

**Login Demo:**
1. Enter any phone number or email (e.g., `+1 (555) 123-4567` or `user@example.com`)
2. Click "Send OTP"
3. A demo OTP will be displayed on screen (e.g., `123456`)
4. Enter the OTP and click "Verify & Login"
5. Upload a video and watch real-time detection!

---

## 🐳 Docker Compose Setup (Production)

### **Full Stack with Docker**

```bash
cd scanconvey

# Build and run all services
docker-compose up --build

# Services will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Java Service: http://localhost:9090 (if enabled)
```

**What starts:**
- ✅ Frontend (Nginx on port 3000)
- ✅ Backend (FastAPI on port 8000)
- ✅ Java Service (optional, port 9090)
- ✅ SQLite database (persistent)

### **Production Deployment**

```bash
# Build production images
docker-compose -f docker-compose.yml build

# Run with production settings
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

---

## 🔑 Authentication Flow

### OTP-Based Login

```
User Input (Phone/Email)
        ↓
[Backend: Generate 6-digit OTP]
        ↓
[Store in SQLite with 10min expiry]
        ↓
[Display OTP on screen - Demo only]
        ↓
User enters OTP
        ↓
[Backend: Verify OTP + Create Session]
        ↓
[Return session_token + user_id]
        ↓
[Frontend: Save to localStorage]
        ↓
✅ Authenticated!
```

**Database Schema:**
```sql
users {
  id, phone_email (UNIQUE), otp_code, otp_expires_at, created_at
}

sessions {
  id, user_id, session_token (UNIQUE), created_at, expires_at (7 days)
}

video_logs {
  id, session_id, filename, boxes_count, packets_count, parcels_count,
  total_count, defects_count, processed_frames, total_frames,
  started_at, finished_at
}
```

---

## 🎯 Belt Region Detection

### How It Works

```
Frame Input
   ↓
[ConveyorBeltDetector: Auto-detect belt bounds]
   ↓ (Belt region: 35%-85% of frame height)
[Filter contours: Only those on belt]
   ↓
[MOG2 + Morphological ops]
   ↓
[Centroid Tracking]
   ↓
[Count crossing line: Only belt objects!]
   ↓
✅ Accurate count (background ignored)
```

**Key Improvements:**
- ✅ Ignores clutter in background (above/below belt)
- ✅ Visible belt region boundaries in annotation
- ✅ Configurable belt area (edit `belt_top` / `belt_bottom`)

---

## 📊 Video Logs API

### Get Processing History

```bash
curl -X GET "http://localhost:8000/logs/{session_token}"
```

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "filename": "conveyor_video_001.mp4",
      "boxes": 45,
      "packets": 23,
      "parcels": 12,
      "total": 80,
      "defects": 2,
      "started_at": "2024-06-17T10:30:00+00:00",
      "finished_at": "2024-06-17T10:35:15+00:00"
    }
  ],
  "total_videos": 1
}
```

---

## 🔧 Configuration

### Backend Settings (`backend/main.py`)

```python
# Conveyor Belt Region (as % of frame height)
belt_top = int(frame_height * 0.35)      # 35% from top
belt_bottom = int(frame_height * 0.85)   # 85% from top

# MOG2 Background Subtraction
history=120          # Higher = slower adaptation
varThreshold=50      # Lower = more sensitive
detectShadows=True   # Remove shadows

# Tracking
max_dist_frac=0.18   # Max centroid distance fraction
max_ghost=10         # Frames to keep track alive after loss

# Counting Line
LINE_Y = int(fh * 0.60)  # 60% down frame
```

### Frontend Environment (`.env`)

```env
VITE_API_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🎬 Processing Pipeline

### Frame Processing Stages

1. **Background Subtraction (MOG2)**
   - Adaptive foreground mask
   - Shadow removal

2. **Morphological Operations**
   - MORPH_OPEN: Remove speckles (5×5 kernel)
   - MORPH_CLOSE: Fill holes (15×15 kernel)
   - DILATE: Expand blobs (3 iterations)

3. **Contour Detection**
   - Extract external contours
   - Filter by min area (0.1% of frame)
   - Aspect ratio guard (0.1-8.0)

4. **Belt Region Constraint** ⭐ NEW
   - Apply belt region mask
   - Only track objects on belt

5. **Centroid Tracking**
   - Assign persistent IDs
   - Direction enforcement (downward only)
   - Ghost frames (8-10 frames)

6. **Counting**
   - When centroid crosses LINE_Y
   - Classify by area (Box/Packet/Parcel)
   - Update counts

7. **Defect Detection**
   - Run YOLOv8 every 10 frames
   - Detect cracks, misalignment, missing components

8. **Logging**
   - Store counts + metadata in SQLite
   - Automatic after processing

---

## 📈 Performance Metrics

| Component | Spec |
|-----------|------|
| **Backend API** | FastAPI (async) |
| **Frontend** | React 18 + Vite |
| **Video Processing** | Real-time with SSE streaming |
| **Object Detection** | YOLOv8-nano (10 FPS) |
| **Tracking** | Centroid-based (60+ FPS) |
| **Database** | SQLite (lightweight) |
| **Auth** | OTP (6-digit, 10min expiry) |

---

## 🐛 Troubleshooting

### Backend Issues

**"Cannot open video file"**
```bash
# Install ffmpeg
apt-get install ffmpeg          # Linux
brew install ffmpeg             # macOS
# Windows: Download from ffmpeg.org
```

**"ModuleNotFoundError: No module named 'ultralytics'"**
```bash
pip install --upgrade ultralytics opencv-python
```

**"Port 8000 already in use"**
```bash
# Change port in uvicorn
uvicorn main:app --port 8001
```

### Frontend Issues

**"CORS Error"**
- Backend already has CORS enabled
- Ensure API_URL in .env is correct
- Check backend is running

**"Blank login page"**
- Check browser console (F12) for errors
- Verify VITE_API_URL points to backend
- Restart dev server: `npm run dev`

### Database Issues

**"Database locked"**
```bash
# Remove database and restart
rm /tmp/scanconvey_db.sqlite
```

---

## 🚀 Advanced Usage

### Custom YOLOv8 Model

```python
# In backend/main.py
_yolo_model = YOLO("yolov8m.pt")  # Use medium model instead
```

### Enable SMTP for Real OTP

```python
import smtplib
from email.mime.text import MIMEText

def send_email_otp(email, otp_code):
    msg = MIMEText(f"Your OTP: {otp_code}")
    msg['Subject'] = 'ScanConvey Login'
    msg['From'] = "noreply@scanconvey.com"
    msg['To'] = email
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login("your-email@gmail.com", "app-password")
        server.send_message(msg)
```

---

## 📝 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/send-otp` | ❌ | Send OTP to phone/email |
| POST | `/auth/verify-otp` | ❌ | Verify OTP & create session |
| POST | `/auth/logout` | ✅ | Logout user |
| POST | `/upload` | ✅ | Upload video for processing |
| GET | `/stream/{job_id}` | ✅ | SSE stream of processing |
| GET | `/result/{job_id}` | ✅ | Get final result |
| POST | `/log-video` | ✅ | Log processed video |
| GET | `/logs/{session_token}` | ✅ | Get user's video history |
| GET | `/health` | ❌ | Health check |

---

## 📦 Project Structure

```
scanconvey/
├── backend/
│   ├── main.py                 # FastAPI + Detection Logic
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main app with auth flow
│   │   ├── components/
│   │   │   ├── LoginPage.tsx    # OTP login portal
│   │   │   ├── VideoLogs.tsx    # History viewer
│   │   │   ├── UploadZone.tsx   # Drag-drop upload
│   │   │   └── ProgressBar.tsx
│   │   ├── hooks/
│   │   │   └── useCounter.ts    # Detection logic hook
│   │   └── api/
│   │       └── api.ts           # API client
│   ├── index.html
│   ├── package.json
│   └── Dockerfile
├── java-service/               # Optional gRPC service
├── docker-compose.yml
└── README.md
```

---

## 🎯 Next Steps

1. **Deploy to Cloud**
   - AWS EC2 + RDS
   - Google Cloud Run
   - DigitalOcean App Platform

2. **Integrate Real SMS/Email**
   - Twilio for SMS OTP
   - SendGrid for Email

3. **Add Admin Dashboard**
   - Analytics
   - User management
   - Video analytics

4. **Mobile App**
   - React Native version
   - Real-time notifications

---

## 📞 Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review API responses in browser DevTools
- Test endpoints with curl/Postman

---

## 📄 License

Secuodsoft Technologies - Internship Project

---

**Version:** 4.0.0  
**Last Updated:** June 2024  
**Maintainer:** Shru (GitHub: @shrutayyy07)
