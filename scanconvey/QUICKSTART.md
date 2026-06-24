# ScanConvey - Quick Start Guide ⚡

Get running in **5 minutes**!

## Prerequisites Check

```bash
# Python 3.9+
python --version

# Node.js 16+
node --version

# FFmpeg (for video processing)
ffmpeg -version
```

**Missing FFmpeg?**
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

---

## ⚡ 3-Step Setup

### Step 1: Backend (Terminal 1)

```bash
cd scanconvey/backend

# Setup Python env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install & run
pip install -r requirements.txt
uvicorn main:app --reload

# 🎉 Backend ready at http://localhost:8000
```

### Step 2: Frontend (Terminal 2)

```bash
cd scanconvey/frontend

# Setup Node
npm install

# Create config
echo "VITE_API_URL=http://localhost:8000" > .env

# Run
npm run dev

# 🎉 Frontend ready at http://localhost:5173
```

### Step 3: Open Browser

```
http://localhost:5173
```

---

## 🔓 Demo Login

**Any of these work:**

| Input | Role |
|-------|------|
| `+1 555 123 4567` | Demo phone |
| `user@example.com` | Demo email |

1. Enter phone/email → Click "Send OTP"
2. Copy the **OTP code** shown on screen (e.g., `123456`)
3. Paste it in the OTP field → Click "Verify & Login"
4. **You're in!** 🚀

---

## 📹 Test It Out

1. **Download sample video** or use any `.mp4` file (~10-30 seconds)
2. **Click upload zone** in the app
3. **Watch live detection** in real-time
4. **View results** with counts broken down by object type

---

## 🎬 Sample Video

Need a test video? Create one:

```bash
# Using ffmpeg (create 5-second video with patterns)
ffmpeg -f lavfi -i testsrc=size=640x480:duration=5 -f lavfi -i sine=f=440 \
  -pix_fmt yuv420p -y sample.mp4
```

Or **download from internet** - any conveyor belt video works!

---

## 📊 Key Features to Try

### ✅ Login Portal
- Phone/Email based authentication
- OTP sent to console (demo mode)
- Auto-saves session in browser

### ✅ Video Processing
- Drag & drop upload
- Real-time SSE streaming
- Live frame annotation with:
  - 🟠 Boxes (orange)
  - 🟢 Packets (green)
  - 🔵 Parcels (blue)
  - 🔴 Defects (red)

### ✅ Belt Region Detection
- Shows **green boundary** of valid counting area
- Ignores background clutter
- Only counts objects on conveyor

### ✅ Video History
- Click **"Logs"** button in header
- See all past processing results
- Category-wise breakdown (boxes, packets, parcels, defects)

---

## 🆘 Troubleshooting

### "Cannot find module uvicorn"
```bash
pip install -r requirements.txt --upgrade
```

### "Port 8000 already in use"
```bash
# Use different port
uvicorn main:app --port 8001 --reload
# Update .env in frontend: VITE_API_URL=http://localhost:8001
```

### "No module named opencv"
```bash
pip install opencv-python-headless
```

### "Frontend won't load"
```bash
# Clear cache & reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

## 📁 File Locations

| What | Where |
|------|-------|
| Backend | `scanconvey/backend/main.py` |
| Frontend | `scanconvey/frontend/src/App.tsx` |
| Config | `scanconvey/frontend/.env` |
| Logs | `scanconvey/logs/` (created after processing) |
| Database | `/tmp/scanconvey_db.sqlite` |

---

## 🐳 Prefer Docker?

```bash
cd scanconvey
docker-compose up --build

# Access at:
# - http://localhost:3000 (Frontend)
# - http://localhost:8000 (Backend)
```

---

## 📞 Next Steps

- Read full docs: `SETUP.md`
- Explore API: `http://localhost:8000/docs`
- Check logs: Open browser DevTools (F12)

---

**Ready?** Let's go! 🚀
