# ScanConvey — Conveyor Packet Counter

A full-stack application that detects and counts **blue-white medical packets**
moving along a conveyor belt by analysing an uploaded video file.

> **v4.2.0** — Packet-specific counting mode with ROI validation, bounding-box
> smoothing, false-positive rejection, and minimum-age track guards.

---

## Architecture

```
scanconvey/
├── frontend/          React 18 + Vite + TypeScript + Tailwind
├── backend/           Python FastAPI + OpenCV + YOLOv8
├── java-service/      Spring Boot WebFlux + gRPC + Rule Engine + Audit
├── proto/             conveyor.proto — shared Protobuf contract
└── docker-compose.yml Multi-container production build
```

## Tech Stack

| Week | Component               | Technology                                       |
|------|-------------------------|--------------------------------------------------|
| 1    | Reactive ingestion      | Spring WebFlux, Project Reactor, Virtual Threads |
| 2    | Streaming interface     | React SSE client, FastAPI StreamingResponse      |
| 3    | Interop tunnel          | gRPC, Protocol Buffers (.proto)                  |
| 4    | Computer vision         | Python OpenCV MOG2, morphology, centroid tracker |
| 5    | Defect classification   | YOLOv8-nano (ultralytics)                        |
| 6    | Rule engine             | Java rule engine, rolling-window defect metrics  |
| 7    | Audit logging           | Java NIO FileChannel, ReentrantLock, Markdown    |
| 8    | Production build        | Docker Compose multi-container                   |

---

## Detection Configuration (v4.2.0)

The backend exposes a single `DETECTION_CONFIG` dict in `backend/main.py`
that controls every detection parameter.  All pixel values are calibrated
for an 854 × 480 (480p) reference resolution and are automatically scaled
to the actual video dimensions at runtime.

```python
DETECTION_CONFIG = {
    # Belt ROI (pixels, 854×480 reference)
    "BELT_X_MIN": 180,
    "BELT_X_MAX": 1520,
    "BELT_Y_MIN": 180,
    "BELT_Y_MAX": 760,

    # Packet bounding-box size limits
    "PACKET_MIN_WIDTH":  120,
    "PACKET_MAX_WIDTH":  320,
    "PACKET_MIN_HEIGHT":  80,
    "PACKET_MAX_HEIGHT": 220,

    # Contour area limits (pixels²)
    "PACKET_MIN_AREA":  10000,
    "PACKET_MAX_AREA":  70000,

    # Width / height aspect ratio (landscape packets)
    "PACKET_MIN_ASPECT_RATIO": 1.2,
    "PACKET_MAX_ASPECT_RATIO": 3.5,

    # Track must exist for this many frames before being counted
    "MIN_TRACK_FRAMES": 5,

    # EMA smoothing weight on new bounding-box measurement (0–1)
    "SMOOTHING_ALPHA": 0.7,
}
```

### What is rejected and why

| Rejected object        | Rejection gate                                      |
|------------------------|-----------------------------------------------------|
| Belt edges / rails     | Aspect ratio outside 1.2–3.5, or area too small    |
| Machine parts / motors | Area > PACKET_MAX_AREA or outside belt ROI          |
| Shadows                | MOG2 shadow pixels (value 127) zeroed before morphology |
| Reflections / glints   | Area < PACKET_MIN_AREA                             |
| Background objects     | Centroid outside BELT_X/Y_MIN–MAX ROI              |
| Noise blobs            | Open morphology (5×5 kernel) removes speckles      |
| Transient detections   | Track age < MIN_TRACK_FRAMES not counted           |
| Static background blobs| Net downward movement < 15 px required to count    |
| Double-counts          | Once a track ID is in counted_ids it is locked     |

---

## How to run

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

Services:

- Frontend:        http://localhost:3000
- Python API:      http://localhost:8000
- Python API docs: http://localhost:8000/docs
- Java REST:       http://localhost:8080
- gRPC:            localhost:9090

```bash
docker compose down -v   # stop and clean up
```

---

### Option B — Local development

#### Terminal 1 — Java service

Prerequisites: JDK 21, Maven 3.9+

```bash
cd java-service
mvn package -DskipTests
java -jar target/java-service-1.0.0.jar
```

#### Terminal 2 — Python backend

Prerequisites: Python 3.11–3.12 recommended (3.13+ supported)

```bash
cd backend

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Generate gRPC stubs
python -m grpc_tools.protoc -I ../proto --python_out=. --grpc_python_out=. ../proto/conveyor.proto

uvicorn main:app --reload --port 8000
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m grpc_tools.protoc -I ../proto --python_out=. --grpc_python_out=. ../proto/conveyor.proto
uvicorn main:app --reload --port 8000
```

#### Terminal 3 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## API reference

### Python backend (port 8000)

| Method | Endpoint            | Description                            |
|--------|---------------------|----------------------------------------|
| POST   | /upload             | Upload video → returns job_id          |
| GET    | /stream/{job_id}    | SSE stream: progress + live counts     |
| GET    | /result/{job_id}    | Final counts after processing          |
| GET    | /health             | Liveness + feature flags               |
| POST   | /auth/send-otp      | Send OTP to phone / e-mail             |
| POST   | /auth/verify-otp    | Verify OTP → session token             |
| POST   | /auth/logout        | Invalidate session                     |
| POST   | /log-video          | Persist a completed job to audit DB    |
| GET    | /logs/{token}       | Fetch all video logs for a user        |

### SSE event shape (`/stream/{job_id}`)

```json
{
  "type": "progress",
  "frame": 42,
  "total": 120,
  "progress": 35.0,
  "boxes": 0,
  "packets": 3,
  "parcels": 0,
  "detections": 2,
  "defects": 0,
  "halt": false,
  "halt_reason": "",
  "frame_b64": "<jpeg base64>"
}
```

Final event type is `"done"`.

### Java service (port 8080)

| Method | Endpoint            | Description                         |
|--------|---------------------|-------------------------------------|
| POST   | /telemetry          | Ingest telemetry (reactive)         |
| GET    | /telemetry/stream   | SSE stream of rule-engine events    |
| GET    | /telemetry/health   | Liveness check                      |

### gRPC (port 9090)

Service: `conveyor.ConveyorTelemetry`  
Method:  `StreamTelemetry` (bidirectional streaming)  
Schema:  `proto/conveyor.proto`

---

## Tuning the detector

Edit `DETECTION_CONFIG` in `backend/main.py`.  No other file needs to change.

| Parameter               | Effect                                                  |
|-------------------------|---------------------------------------------------------|
| `BELT_*`                | Restrict the detection zone to the physical belt        |
| `PACKET_MIN/MAX_WIDTH`  | Accept packets wider/narrower than current calibration  |
| `PACKET_MIN/MAX_HEIGHT` | Accept taller/shorter packets                           |
| `PACKET_MIN/MAX_AREA`   | Relax/tighten on total packet area                      |
| `PACKET_MIN/MAX_ASPECT_RATIO` | Change the allowed width:height ratio range       |
| `MIN_TRACK_FRAMES`      | Higher = fewer false counts; lower = count faster       |
| `SMOOTHING_ALPHA`       | Higher = snappier boxes; lower = smoother but laggy     |

---

## Audit logs

When running locally, incident and telemetry compliance logs are written to:

```
java-service/audit/incidents.md
java-service/audit/telemetry.md
```

In Docker, logs are persisted in the `audit-logs` named volume.

---

## Notes on YOLOv8

On first run, `yolov8n.pt` (~6 MB) is downloaded automatically by the
ultralytics library.  The defect classification uses COCO class proxies.
In production, replace `yolov8n.pt` with a custom-trained model and update
`DEFECT_CLASS_PROXY` in `backend/main.py`.

---

*Secuodsoft Technologies Internship Project — ScanConvey v4.2.0*
