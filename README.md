# ScanConvey
It is a full-stack application that counts **blue & white packets** on a conveyor belt by analysing an uploaded video file.

## Tech Stack
- **Frontend** — React 18 + Vite + TypeScript + Tailwind CSS
- **Backend** — Python FastAPI + OpenCV + YOLOv8
- **Java Service** — Spring Boot WebFlux + gRPC + Rule Engine
- **Infra** — Docker Compose

## How to run
### Docker

```bash
git clone https://github.com/<your-org>/scanconvey.git
cd scanconvey
docker compose up --build
```

| Service     | URL                        |
|-------------|----------------------------|
| Frontend    | http://localhost:3000      |
| Backend API | http://localhost:8000      |
| API Docs    | http://localhost:8000/docs |
| Java Service| http://localhost:8080      |

### Local Dev

**Terminal 1 — Java service** (requires JDK 21, Maven 3.9+)
```bash
cd java-service
mvn package -DskipTests
java -jar target/java-service-1.0.0.jar
```

**Terminal 2 — Python backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m grpc_tools.protoc -I ../proto --python_out=. --grpc_python_out=. ../proto/conveyor.proto
uvicorn main:app --reload --port 8000
```

**Terminal 3 — Frontend**
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev   # http://localhost:5173
```

## Demo Login

Enter `user@example.com` or `+1 555 123 4567`, click **Send OTP**, type the demo otp displayed on your screen and log in.

## Screenshots
### Login Page
<img width="1920" height="1080" alt="Screenshot (939)" src="https://github.com/user-attachments/assets/d8dae258-2339-4d06-adbf-7dcf52352412" />

### OTP Authentication
<img width="1920" height="1080" alt="Screenshot (940)" src="https://github.com/user-attachments/assets/255ba808-658f-438f-8f3d-f6ecf22359d2" />

### Upload Dashboard
<img width="1920" height="1080" alt="Screenshot (944)" src="https://github.com/user-attachments/assets/9ce254d8-386f-476b-95bb-74012dc3bd3b" />

### Live Video Analysis Feed
<img width="1920" height="1080" alt="Screenshot (942)" src="https://github.com/user-attachments/assets/39280428-f2b4-4b4b-a6f9-abb229232d27" />

### Video Logs History:
<img width="1920" height="1080" alt="Screenshot (943)" src="https://github.com/user-attachments/assets/b592adaa-eeed-4f73-85c8-d4c84de91aef" />


## Features
- OTP-based authentication 
- Drag-and-drop video upload
- Live frame-by-frame detection streamed to the browser
- Counts boxes, packets, parcels, and flags defects
- Belt ROI validation — ignores everything outside the conveyor zone
- Defect rule engine with production halt alerts
- Per-user video history and audit logs


## Project Structure

```
scanconvey/
├── backend/          # FastAPI + OpenCV pipeline
├── frontend/         # React SPA
├── java-service/     # Spring Boot rule engine + gRPC
├── proto/            # Shared Protobuf contract
└── docker-compose.yml
```

---
## Author:
Shruti Samal(shrutayyy07)
*Secuodsoft Technologies Internship Project — ScanConvey
