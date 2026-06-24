"""
ScanConvey - Python FastAPI Backend
v4.3.0: Accurate per-packet counting — zone-entry model, aggressive blob merge,
        wider tracker tolerance, track-ID display, real-time count overlay.
"""

import os, uuid, json, base64, asyncio, tempfile, threading, time, sqlite3, secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer

try:
    import grpc, conveyor_pb2, conveyor_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False

try:
    from ultralytics import YOLO
    _yolo_model: Optional[object] = None
    def _get_yolo():
        global _yolo_model
        if _yolo_model is None:
            _yolo_model = YOLO("yolov8n.pt")
        return _yolo_model
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    def _get_yolo(): return None

app = FastAPI(title="ScanConvey API", version="4.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = Path(tempfile.gettempdir()) / "scanconvey_db.sqlite"
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, phone_email TEXT UNIQUE NOT NULL,
        otp_code TEXT, otp_expires_at REAL, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY, user_id INTEGER, session_token TEXT UNIQUE,
        created_at TEXT, expires_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS video_logs (
        id INTEGER PRIMARY KEY, session_id INTEGER, filename TEXT,
        boxes_count INTEGER, packets_count INTEGER, parcels_count INTEGER,
        total_count INTEGER, defects_count INTEGER,
        processed_frames INTEGER, total_frames INTEGER,
        started_at TEXT, finished_at TEXT, FOREIGN KEY(session_id) REFERENCES sessions(id))""")
    conn.commit(); conn.close()

init_db()

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
UPLOAD_DIR = Path(tempfile.gettempdir()) / "conveyor_counter"
UPLOAD_DIR.mkdir(exist_ok=True)
JAVA_GRPC_HOST = os.getenv("JAVA_GRPC_HOST", "java-service")
JAVA_GRPC_PORT = int(os.getenv("JAVA_GRPC_PORT", "9090"))

PACKET_COLOR  = (50, 220, 100)   # bright green
COUNTED_COLOR = (255, 200, 0)    # cyan (BGR) — packet already counted
DEFECT_COLOR  = (60, 60, 255)
LINE_COLOR    = (0, 200, 255)
ROI_COLOR     = (80, 180, 80)
FRAME_PUSH_INTERVAL = 3          # push annotated frame every N frames (was 5)

# ── Detection config ──────────────────────────────────────────────────────────
# All pixel values are for 854×480 reference; auto-scaled to actual resolution.
DETECTION_CONFIG = {
    "BELT_X_MIN":   130,
    "BELT_X_MAX":   720,
    "BELT_Y_MIN":   185,   # top of belt surface
    "BELT_Y_MAX":   315,   # bottom of belt (above red machinery)

    # Generous size range — partial/occluded packets must still get a box
    "PACKET_MIN_WIDTH":   55,
    "PACKET_MAX_WIDTH":  500,
    "PACKET_MIN_HEIGHT":  35,
    "PACKET_MAX_HEIGHT": 270,

    "PACKET_MIN_AREA":  2000,
    "PACKET_MAX_AREA": 130000,

    # Very permissive aspect ratio — one packet can look square or very wide
    "PACKET_MIN_ASPECT_RATIO": 0.4,
    "PACKET_MAX_ASPECT_RATIO": 7.0,

    # Only need 2 consecutive frames to confirm a real track
    "MIN_TRACK_FRAMES": 2,

    "SMOOTHING_ALPHA": 0.5,
}

_REF_W, _REF_H = 854, 480


def _scale_config(fw: int, fh: int) -> dict:
    sx, sy = fw / _REF_W, fh / _REF_H
    s_area = sx * sy
    cfg = dict(DETECTION_CONFIG)
    for k in ("BELT_X_MIN", "BELT_X_MAX", "PACKET_MIN_WIDTH", "PACKET_MAX_WIDTH"):
        cfg[k] = int(cfg[k] * sx)
    for k in ("BELT_Y_MIN", "BELT_Y_MAX", "PACKET_MIN_HEIGHT", "PACKET_MAX_HEIGHT"):
        cfg[k] = int(cfg[k] * sy)
    cfg["PACKET_MIN_AREA"] = int(cfg["PACKET_MIN_AREA"] * s_area)
    cfg["PACKET_MAX_AREA"] = int(cfg["PACKET_MAX_AREA"] * s_area)
    return cfg


# ── Packet Validator ──────────────────────────────────────────────────────────
class PacketValidator:
    def __init__(self, fw: int, fh: int):
        self.fw, self.fh = fw, fh
        self.cfg = _scale_config(fw, fh)
        self.belt_mask = np.zeros((fh, fw), dtype=np.uint8)
        cv2.rectangle(self.belt_mask,
                      (self.cfg["BELT_X_MIN"], self.cfg["BELT_Y_MIN"]),
                      (self.cfg["BELT_X_MAX"], self.cfg["BELT_Y_MAX"]), 255, -1)

    @property
    def belt_top(self):    return self.cfg["BELT_Y_MIN"]
    @property
    def belt_bottom(self): return self.cfg["BELT_Y_MAX"]
    @property
    def belt_left(self):   return self.cfg["BELT_X_MIN"]
    @property
    def belt_right(self):  return self.cfg["BELT_X_MAX"]

    def is_valid_packet(self, cnt) -> bool:
        cfg = self.cfg
        area = cv2.contourArea(cnt)
        if not (cfg["PACKET_MIN_AREA"] <= area <= cfg["PACKET_MAX_AREA"]):
            return False
        bx, by, bw, bh = cv2.boundingRect(cnt)
        if not (cfg["PACKET_MIN_WIDTH"]  <= bw <= cfg["PACKET_MAX_WIDTH"]):
            return False
        if not (cfg["PACKET_MIN_HEIGHT"] <= bh <= cfg["PACKET_MAX_HEIGHT"]):
            return False
        aspect = bw / max(bh, 1)
        if not (cfg["PACKET_MIN_ASPECT_RATIO"] <= aspect <= cfg["PACKET_MAX_ASPECT_RATIO"]):
            return False
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            return False
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        if not (cfg["BELT_X_MIN"] <= cx <= cfg["BELT_X_MAX"] and
                cfg["BELT_Y_MIN"] <= cy <= cfg["BELT_Y_MAX"]):
            return False
        return True

    def centroid(self, cnt):
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            return None
        return M["m10"] / M["m00"], M["m01"] / M["m00"]


# ── Bounding-Box Smoother ─────────────────────────────────────────────────────
class BBoxSmoother:
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self._state: dict[int, np.ndarray] = {}

    def update(self, tid: int, bbox: tuple) -> tuple:
        new = np.array(bbox, dtype=float)
        if tid not in self._state:
            self._state[tid] = new
        else:
            self._state[tid] = self.alpha * new + (1.0 - self.alpha) * self._state[tid]
        return tuple(int(v) for v in self._state[tid])

    def remove(self, tid: int):
        self._state.pop(tid, None)


def _merge_close_boxes(detections: list[tuple], dist_thresh: float) -> list[tuple]:
    if not detections:
        return []
    n = len(detections)
    parent = list(range(n))

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    def boxes_are_close(b1, b2):
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        l1, r1, t1, b_1 = x1, x1 + w1, y1, y1 + h1
        l2, r2, t2, b_2 = x2, x2 + w2, y2, y2 + h2
        x_dist = max(0, l2 - r1) if l2 >= r1 else max(0, l1 - r2)
        y_dist = max(0, t2 - b_1) if t2 >= b_1 else max(0, t1 - b_2)
        return x_dist < dist_thresh and y_dist < dist_thresh

    for i in range(n):
        for j in range(i + 1, n):
            _, _, bx1, by1, bw1, bh1 = detections[i]
            _, _, bx2, by2, bw2, bh2 = detections[j]
            if boxes_are_close((bx1, by1, bw1, bh1), (bx2, by2, bw2, bh2)):
                union(i, j)

    groups = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(detections[i])

    merged = []
    for root, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            min_x = min(d[2] for d in group)
            min_y = min(d[3] for d in group)
            max_r = max(d[2] + d[4] for d in group)
            max_b = max(d[3] + d[5] for d in group)
            merged_bw = max_r - min_x
            merged_bh = max_b - min_y
            merged_cx = min_x + merged_bw / 2
            merged_cy = min_y + merged_bh / 2
            merged.append((merged_cx, merged_cy, min_x, min_y, merged_bw, merged_bh))
    return merged


def _now_iso(): return datetime.now(timezone.utc).isoformat()

def _new_job(video_path, total_frames, fps):
    return {
        "video_path": video_path, "total_frames": total_frames, "fps": fps,
        "processed": 0, "boxes": 0, "packets": 0, "parcels": 0,
        "defects": [], "halt": False, "halt_reason": "",
        "done": False, "error": None, "events": [],
        "started_at": _now_iso(), "finished_at": None,
    }

DEFECT_CLASS_PROXY = {
    "crack": [56, 57], "misalignment": [63, 64], "missing_component": [73, 74]
}

def _run_yolo_on_frame(frame, validator: PacketValidator):
    if not YOLO_AVAILABLE: return []
    model = _get_yolo()
    results = model(frame, verbose=False, conf=0.25)[0]
    defects = []
    h, w = frame.shape[:2]
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf   = float(box.conf[0])
        defect_type = next((dt for dt, ids in DEFECT_CLASS_PROXY.items() if cls_id in ids), "")
        if not defect_type: continue
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        
        # Only retain defects whose centroid is within the conveyor belt ROI
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        if not (validator.belt_left <= cx <= validator.belt_right and
                validator.belt_top <= cy <= validator.belt_bottom):
            continue
            
        defects.append({
            "defect_type": defect_type, "confidence": round(conf, 4),
            "bbox_px": (int(x1), int(y1), int(x2), int(y2)),
            "bbox": {"x": round(x1/w,3), "y": round(y1/h,3),
                     "w": round((x2-x1)/w,3), "h": round((y2-y1)/h,3)},
        })
    return defects


def _annotate_frame(frame, detected, defects, line_y, packets,
                    frame_idx, total, validator: PacketValidator, counted_ids: set):
    out = frame.copy()
    h, w = out.shape[:2]

    # Draw packets in royal blue (255, 120, 0 in BGR)
    BLUE_COLOR = (255, 120, 0)
    for d in detected:
        bx = int(d["bbox"]["x"] * w); by = int(d["bbox"]["y"] * h)
        bw = int(d["bbox"]["w"] * w); bh = int(d["bbox"]["h"] * h)
        tid = d.get("tid", -1)
        
        cv2.rectangle(out, (bx, by), (bx+bw, by+bh), BLUE_COLOR, 2)
        if isinstance(counted_ids, list) and tid in counted_ids:
            label = f"Packet #{counted_ids.index(tid) + 1}"
        elif isinstance(counted_ids, (set, dict)) and tid in counted_ids:
            label = f"Packet #{tid}"
        else:
            label = "Packet"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(out, (bx, by - th - 8), (bx + tw + 6, by), BLUE_COLOR, -1)
        cv2.putText(out, label, (bx + 3, by - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        
        cx = int(d["centroid_x"] * w); cy_px = int(d["centroid_y"] * h)
        cv2.circle(out, (cx, cy_px), 4, (255, 255, 255), -1)
        cv2.circle(out, (cx, cy_px), 4, BLUE_COLOR, 2)

    # Big HUD counter
    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (200, 56), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.65, out, 0.35, 0, out)
    cv2.putText(out, f"Packets: {packets}", (8, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

    prog = f"{frame_idx}/{total}"
    (pw, _), _ = cv2.getTextSize(prog, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
    cv2.putText(out, prog, (w - pw - 6, h - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 160, 160), 1, cv2.LINE_AA)
    return out


def _frame_to_b64(frame, quality=60):
    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return base64.b64encode(buf).decode("ascii")


# ── gRPC ──────────────────────────────────────────────────────────────────────
class GrpcTelemetrySender:
    def __init__(self):
        self._channel = None; self._stub = None
        self._queue: list = []; self._halt = False; self._halt_reason = ""
    def connect(self):
        if not GRPC_AVAILABLE: return
        try:
            self._channel = grpc.insecure_channel(f"{JAVA_GRPC_HOST}:{JAVA_GRPC_PORT}")
            self._stub = conveyor_pb2_grpc.ConveyorTelemetryStub(self._channel)
        except: self._stub = None
    def send(self, msg):
        if self._stub: self._queue.append(msg)
    def stop(self):
        if self._stub: self._queue.append(None)
    def close(self):
        if self._channel: self._channel.close()
    @property
    def halt(self): return self._halt
    @property
    def halt_reason(self): return self._halt_reason

def _build_proto(frame_idx, total, detected, packets):
    if not GRPC_AVAILABLE: return None
    objs = [conveyor_pb2.DetectedObject(
        label=d["label"], centroid_x=d["centroid_x"], centroid_y=d["centroid_y"],
        bbox_x=d["bbox"]["x"], bbox_y=d["bbox"]["y"],
        bbox_w=d["bbox"]["w"], bbox_h=d["bbox"]["h"],
        confidence=d.get("confidence", 1.0), defect_type=d.get("defect_type", "")
    ) for d in detected]
    return conveyor_pb2.FrameTelemetry(
        frame_index=frame_idx, total_frames=total, objects=objs,
        box_count=0, packet_count=packets, parcel_count=0,
        timestamp_ms=int(time.time() * 1000)
    )


# ── Centroid Tracker ──────────────────────────────────────────────────────────
class CentroidTracker:
    """
    Tracks objects across frames by nearest-centroid matching.

    Key improvements in v4.3:
    - max_dist_frac=0.20  wider search radius catches fast-moving / jittery blobs
    - max_ghost=12        keeps tracks alive through 12 frames of occlusion
    - age counter         tracks < MIN_TRACK_FRAMES are not counted
    - net-X motion guard  counts only tracks that moved leftward (packet direction)
    """
    def __init__(self, fw: int, fh: int, max_dist_frac: float = 0.20, max_ghost: int = 12):
        self.fw, self.fh = fw, fh
        diag = (fw**2 + fh**2) ** 0.5
        self.max_dist  = diag * max_dist_frac
        self.max_ghost = max_ghost
        self.tracks: dict[int, dict] = {}
        self.next_id = 0

    def update(self, detections: list[tuple]):
        """
        detections: [(cx, cy, bx, by, bw, bh), ...]
        Returns (active_dict, removed_ids)
        """
        centroids  = [(d[0], d[1]) for d in detections]
        det_bboxes = [(d[2], d[3], d[4], d[5]) for d in detections]

        unmatched_det   = list(range(len(centroids)))
        matched_tracks: set[int] = set()

        if centroids and self.tracks:
            costs = []
            for det_i, (cx, cy) in enumerate(centroids):
                for tid, t in self.tracks.items():
                    dist = ((cx - t["cx"])**2 + (cy - t["cy"])**2) ** 0.5
                    if dist < self.max_dist:
                        costs.append((dist, det_i, tid))
            costs.sort()
            matched_det: set[int] = set()
            for _, det_i, tid in costs:
                if det_i in matched_det or tid in matched_tracks:
                    continue
                cx, cy = centroids[det_i]
                t = self.tracks[tid]
                t["history"].append((cx, cy))
                t.update({"cx": cx, "cy": cy, "ghost": 0,
                           "age": t["age"] + 1, "bbox": det_bboxes[det_i]})
                matched_det.add(det_i)
                matched_tracks.add(tid)
            unmatched_det = [i for i in unmatched_det if i not in matched_det]

        for i in unmatched_det:
            cx, cy = centroids[i]
            self.tracks[self.next_id] = {
                "cx": cx, "cy": cy, "ghost": 0,
                "history": [(cx, cy)], "age": 1, "bbox": det_bboxes[i],
            }
            self.next_id += 1

        removed = []
        for tid in list(self.tracks.keys()):
            if tid not in matched_tracks:
                self.tracks[tid]["ghost"] += 1
                if self.tracks[tid]["ghost"] > self.max_ghost:
                    removed.append(tid)
                    del self.tracks[tid]

        active = {
            tid: {"cx": t["cx"], "cy": t["cy"],
                  "age": t["age"], "bbox": t["bbox"]}
            for tid, t in self.tracks.items()
            if t["ghost"] == 0
        }
        return active, removed

    def net_x_motion(self, tid: int) -> float:
        """Negative = moved left (packet direction on this belt)."""
        h = self.tracks.get(tid, {}).get("history", [])
        if len(h) < 2: return 0.0
        return h[-1][0] - h[0][0]

    def net_y_motion(self, tid: int) -> float:
        h = self.tracks.get(tid, {}).get("history", [])
        if len(h) < 2: return 0.0
        return abs(h[-1][1] - h[0][1])


# ── Video Processing ──────────────────────────────────────────────────────────
def _process_video(job_id: str):
    with _jobs_lock:
        job = _jobs[job_id]

    sender = GrpcTelemetrySender()
    sender.connect()

    cap = cv2.VideoCapture(job["video_path"])
    if not cap.isOpened():
        with _jobs_lock:
            _jobs[job_id]["error"] = "Cannot open video file"
            _jobs[job_id]["done"]  = True
        return

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    fw    = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Vertical counting line at 50% of frame
    LINE_Y = int(fh * 0.50)

    # ── MOG2 ──────────────────────────────────────────────────────────────────
    # history=60: very short so packets already on belt at frame 1 are detected.
    # varThreshold=20: sensitive — blue/white packets on dark belt have moderate
    #   contrast; too high a threshold silently drops them.
    fgbg = cv2.createBackgroundSubtractorMOG2(
        history=60, varThreshold=20, detectShadows=True
    )

    # ── Morphology kernels ─────────────────────────────────────────────────────
    # OPEN  (3×3)  — kill salt-and-pepper noise
    # CLOSE (27×27) — close interior gaps in the large white packet face
    # DILATE (9×9, 4 iter) — aggressively merge fragmented sub-contours of
    #   one physical packet into a single blob before findContours
    k_open   = cv2.getStructuringElement(cv2.MORPH_RECT,    (3,  3))
    k_close  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (27, 27))
    k_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9,  9))

    validator = PacketValidator(fw, fh)
    cfg       = validator.cfg
    smoother  = BBoxSmoother(alpha=cfg["SMOOTHING_ALPHA"])
    tracker   = CentroidTracker(fw, fh, max_dist_frac=0.20, max_ghost=12)

    counted_ids: list[int] = []
    defective_tids: set[int] = set()

    # Zone-entry tracking: record which side of LINE_Y each track started on.
    # Once a track's centroid crosses LINE_Y (top→bottom), count it once.
    # This is more robust than pure "was above, now below" crossing because
    # we also count packets that enter the frame already below LINE_Y.
    track_entry_side: dict[int, str] = {}   # tid -> "above" | "below" | "unknown"

    packets = 0
    all_defects:    list[dict] = []
    latest_defects: list[dict] = []
    frame_idx = 0

    def _push_event(payload: str):
        with _jobs_lock:
            _jobs[job_id]["events"].append(payload)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        # ── Foreground mask ────────────────────────────────────────────────────
        fgmask = fgbg.apply(frame)
        fgmask[fgmask == 127] = 0                                     # zero shadows
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN,  k_open)   # remove speckles
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, k_close)  # fill interior gaps
        fgmask = cv2.dilate(fgmask, k_dilate, iterations=4)           # merge fragments
        fgmask = cv2.bitwise_and(fgmask, validator.belt_mask)         # apply ROI

        contours, _ = cv2.findContours(
            fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        current_detections: list[tuple] = []
        for cnt in contours:
            if not validator.is_valid_packet(cnt):
                continue
            centroid = validator.centroid(cnt)
            if centroid is None:
                continue
            cx, cy = centroid
            bx, by, bw, bh = cv2.boundingRect(cnt)
            current_detections.append((cx, cy, bx, by, bw, bh))

        # Scale distance threshold using horizontal scale sx
        sx = fw / _REF_W
        dist_thresh = int(22 * sx)
        merged_detections = _merge_close_boxes(current_detections, dist_thresh)

        # ── Tracker update ─────────────────────────────────────────────────────
        active, removed_tids = tracker.update(merged_detections)
        for tid in removed_tids:
            smoother.remove(tid)
            track_entry_side.pop(tid, None)

        # Filter active tracks to prune stationary background noise
        for tid in list(active.keys()):
            age = active[tid]["age"]
            net_x = tracker.net_x_motion(tid)
            # If a track has been around for at least 5 frames and has not moved left by at least 4 pixels,
            # it is stationary background clutter. Prune it.
            if age >= 5 and net_x >= -4:
                active.pop(tid, None)
                tracker.tracks.pop(tid, None)
                smoother.remove(tid)
                track_entry_side.pop(tid, None)

        # ── Build annotated detection list ─────────────────────────────────────
        detected_this_frame: list[dict] = []
        for tid, tdata in active.items():
            raw_bbox = tdata["bbox"]
            sb = smoother.update(tid, raw_bbox)
            detected_this_frame.append({
                "tid":        tid,
                "label":      "Packet",
                "bbox":       {"x": round(sb[0]/fw, 3), "y": round(sb[1]/fh, 3),
                               "w": round(sb[2]/fw, 3), "h": round(sb[3]/fh, 3)},
                "centroid_x": round(tdata["cx"]/fw, 4),
                "centroid_y": round(tdata["cy"]/fh, 4),
                "confidence": 1.0, "defect_type": "",
            })

        # ── YOLO defects every 10 frames ──────────────────────────────────────
        if frame_idx % 10 == 0 and YOLO_AVAILABLE:
            latest_defects = _run_yolo_on_frame(frame, validator)
            all_defects.extend(latest_defects)
            
            # Associate defects with packet track IDs
            for df in latest_defects:
                df_x1, df_y1, df_x2, df_y2 = df["bbox_px"]
                df_cx = (df_x1 + df_x2) / 2
                df_cy = (df_y1 + df_y2) / 2
                for tid, t in tracker.tracks.items():
                    bx, by, bw, bh = t["bbox"]
                    if bx <= df_cx <= bx + bw and by <= df_cy <= by + bh:
                        defective_tids.add(tid)
                        
            with _jobs_lock:
                _jobs[job_id]["defects"] = all_defects[-50:]

        # ── Counting: zone-entry model ─────────────────────────────────────────
        # Record entry side on first appearance; count when track crosses LINE_Y.
        # Also count packets that enter the frame already below LINE_Y
        # (i.e., they were never "above" — edge case at clip start).
        for tid, tdata in active.items():
            cy = tdata["cy"]
            age = tdata["age"]

            if tid not in track_entry_side:
                track_entry_side[tid] = "above" if cy < LINE_Y else "below"

            if tid in counted_ids:
                continue
            if age < cfg["MIN_TRACK_FRAMES"]:
                continue

            entry = track_entry_side[tid]

            # Enforce persistent leftward motion (moved left by at least 8 pixels)
            # to filter out stationary background noise that jitters slightly.
            is_moving_left = tracker.net_x_motion(tid) < -8

            # Case 1: started above, crossed to below → count
            if entry == "above" and cy >= LINE_Y:
                if is_moving_left:
                    counted_ids.append(tid)
                    packets += 1

            # Case 2: appeared below LINE_Y from the start (already past count line)
            # Count once it has aged enough to prove it's a real packet
            elif entry == "below" and age >= max(cfg["MIN_TRACK_FRAMES"], 4):
                if is_moving_left:
                    counted_ids.append(tid)
                    packets += 1

            # Fallback Case 3: moved horizontally left by a significant amount (at least 25 pixels)
            # which ensures packets that stay on one side of LINE_Y are still counted correctly
            elif tracker.net_x_motion(tid) < -25:
                counted_ids.append(tid)
                packets += 1

        # ── SSE push ──────────────────────────────────────────────────────────
        if frame_idx % FRAME_PUSH_INTERVAL == 0 or frame_idx == total:
            defective_count = len(defective_tids)
            functional_count = max(0, packets - defective_count)

            with _jobs_lock:
                _jobs[job_id].update({
                    "processed": frame_idx,
                    "boxes": functional_count, # functional packets
                    "packets": packets, # total packets
                    "parcels": 0,
                    "defects_count": defective_count
                })

            annotated = _annotate_frame(
                frame, detected_this_frame, latest_defects,
                LINE_Y, packets, frame_idx, total, validator, counted_ids
            )
            frame_b64    = _frame_to_b64(annotated)
            progress_pct = round(frame_idx / max(total, 1) * 100, 1)

            data = json.dumps({
                "type": "progress", "frame": frame_idx, "total": total,
                "progress": progress_pct,
                "boxes": functional_count,
                "packets": packets,
                "parcels": 0,
                "detections": len(detected_this_frame),
                "defects": defective_count,
                "halt": sender.halt, "halt_reason": sender.halt_reason,
                "frame_b64": frame_b64,
            })
            _push_event(f"data: {data}\n\n")

            proto = _build_proto(frame_idx, total, detected_this_frame, packets)
            if proto: sender.send(proto)

        if sender.halt:
            break

    cap.release()
    sender.stop()
    sender.close()
    try: os.remove(job["video_path"])
    except OSError: pass

    defective_count = len(defective_tids)
    functional_count = max(0, packets - defective_count)

    with _jobs_lock:
        _jobs[job_id].update({
            "processed": total,
            "boxes": functional_count,
            "packets": packets,
            "parcels": 0,
            "defects_count": defective_count,
            "halt": sender.halt, "halt_reason": sender.halt_reason,
            "done": True, "finished_at": _now_iso()
        })
    data = json.dumps({
        "type": "done",
        "boxes": functional_count,
        "packets": packets,
        "parcels": 0,
        "total": packets,
        "defects": defective_count,
        "halt": sender.halt, "halt_reason": sender.halt_reason,
    })
    with _jobs_lock:
        _jobs[job_id]["events"].append(f"data: {data}\n\n")


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": _now_iso(),
            "yolo_available": YOLO_AVAILABLE, "grpc_available": GRPC_AVAILABLE}

@app.post("/upload")
async def upload_video(file: UploadFile = File(...), session_token: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM sessions WHERE session_token = ?", (session_token,))
    session = c.fetchone()
    conn.close()
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(400, "Only video files are accepted.")
    job_id   = str(uuid.uuid4())
    tmp_path = str(UPLOAD_DIR / f"{job_id}_{file.filename}")
    contents = await file.read()
    with open(tmp_path, "wb") as f: f.write(contents)
    cap    = cv2.VideoCapture(tmp_path)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    with _jobs_lock: _jobs[job_id] = _new_job(tmp_path, frames, fps)
    threading.Thread(target=_process_video, args=(job_id,), daemon=True).start()
    return JSONResponse({"job_id": job_id, "total_frames": frames, "fps": fps,
                         "filename": file.filename})

@app.get("/stream/{job_id}")
async def stream_events(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")
    async def generate() -> AsyncGenerator[str, None]:
        last_idx = 0
        while True:
            with _jobs_lock:
                job    = _jobs[job_id]
                events = job["events"][last_idx:]
                done   = job["done"]
                error  = job["error"]
            for evt in events: yield evt
            last_idx += len(events)
            if error:
                yield f'data: {{"type":"error","message":"{error}"}}\n\n'; break
            if done and not events: break
            await asyncio.sleep(0.05)
    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Access-Control-Allow-Origin": "*"})

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    if job_id not in _jobs: raise HTTPException(404, "Job not found")
    with _jobs_lock: job = dict(_jobs[job_id])
    return {
        "job_id": job_id, "done": job["done"],
        "boxes": job["boxes"], "packets": job["packets"], "parcels": job["parcels"],
        "total": job["boxes"] + job["packets"] + job["parcels"],
        "defects": job["defects"], "halt": job["halt"], "halt_reason": job["halt_reason"],
        "processed": job["processed"], "total_frames": job["total_frames"],
        "started_at": job["started_at"], "finished_at": job["finished_at"],
    }

@app.post("/auth/send-otp")
async def send_otp(phone_email: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    otp_code   = str(secrets.randbelow(1000000)).zfill(6)
    expires_at = time.time() + 600
    c.execute("INSERT OR REPLACE INTO users (phone_email, otp_code, otp_expires_at, created_at) VALUES (?, ?, ?, ?)",
              (phone_email, otp_code, expires_at, _now_iso()))
    conn.commit(); conn.close()
    print(f"OTP for {phone_email}: {otp_code}")
    return {"success": True, "message": "OTP sent", "otp": otp_code}

@app.post("/auth/verify-otp")
async def verify_otp(phone_email: str = Form(...), otp_code: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, otp_code, otp_expires_at FROM users WHERE phone_email = ?", (phone_email,))
    user = c.fetchone()
    if not user:
        conn.close(); raise HTTPException(401, "User not found")
    user_id, stored_otp, expires_at = user
    if stored_otp != otp_code or time.time() > expires_at:
        conn.close(); raise HTTPException(401, "Invalid or expired OTP")
    session_token      = secrets.token_urlsafe(32)
    expires_at_session = time.time() + 86400 * 7
    c.execute("INSERT INTO sessions (user_id, session_token, created_at, expires_at) VALUES (?, ?, ?, ?)",
              (user_id, session_token, _now_iso(),
               datetime.fromtimestamp(expires_at_session, tz=timezone.utc).isoformat()))
    c.execute("UPDATE users SET otp_code = NULL, otp_expires_at = NULL WHERE id = ?", (user_id,))
    conn.commit(); conn.close()
    return {"success": True, "session_token": session_token, "user_id": user_id}

@app.post("/auth/logout")
async def logout(session_token: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
    conn.commit(); conn.close()
    return {"success": True}

@app.post("/log-video")
async def log_video(session_token: str = Form(...), job_id: str = Form(...),
                    filename: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM sessions WHERE session_token = ?", (session_token,))
    session = c.fetchone()
    if not session:
        conn.close(); raise HTTPException(401, "Invalid session")
    session_id = session[0]
    if job_id not in _jobs:
        conn.close(); raise HTTPException(404, "Job not found")
    with _jobs_lock: job = _jobs[job_id]
    c.execute("""INSERT INTO video_logs
    (session_id, filename, boxes_count, packets_count, parcels_count,
     total_count, defects_count, processed_frames, total_frames, started_at, finished_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (session_id, filename, job.get("boxes", 0), job.get("packets", 0), 0,
     job.get("packets", 0), job.get("defects_count", 0),
     job["processed"], job["total_frames"], job["started_at"], job["finished_at"]))
    conn.commit(); conn.close()
    return {"success": True, "message": "Video logged"}

@app.get("/logs/{session_token}")
async def get_logs(session_token: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM sessions WHERE session_token = ?", (session_token,))
    session = c.fetchone()
    if not session:
        conn.close(); raise HTTPException(401, "Invalid session")
    session_id = session[0]
    c.execute("""SELECT id, filename, boxes_count, packets_count, parcels_count,
                 total_count, defects_count, started_at, finished_at FROM video_logs
                 WHERE session_id = ? ORDER BY started_at DESC""", (session_id,))
    logs = [{"id": r[0], "filename": r[1], "boxes": r[2], "packets": r[3],
             "parcels": r[4], "total": r[5], "defects": r[6],
             "started_at": r[7], "finished_at": r[8]} for r in c.fetchall()]
    conn.close()
    return {"logs": logs, "total_videos": len(logs)}
