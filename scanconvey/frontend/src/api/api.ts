const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function uploadVideo(file: File, sessionToken: string): Promise<{ job_id: string; total_frames: number; fps: number; filename: string }> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("session_token", sessionToken);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function openEventStream(jobId: string): EventSource {
  return new EventSource(`${BASE}/stream/${jobId}`);
}

export async function getResult(jobId: string) {
  const res = await fetch(`${BASE}/result/${jobId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Authentication
export async function sendOtp(phoneEmail: string): Promise<{ success: boolean; message: string; otp?: string }> {
  const fd = new FormData();
  fd.append("phone_email", phoneEmail);
  const res = await fetch(`${BASE}/auth/send-otp`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function verifyOtp(phoneEmail: string, otpCode: string): Promise<{ success: boolean; session_token: string; user_id: string }> {
  const fd = new FormData();
  fd.append("phone_email", phoneEmail);
  fd.append("otp_code", otpCode);
  const res = await fetch(`${BASE}/auth/verify-otp`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function logout(sessionToken: string): Promise<{ success: boolean }> {
  const fd = new FormData();
  fd.append("session_token", sessionToken);
  const res = await fetch(`${BASE}/auth/logout`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Video Logging
export async function logVideo(sessionToken: string, jobId: string, filename: string): Promise<{ success: boolean; message: string }> {
  const fd = new FormData();
  fd.append("session_token", sessionToken);
  fd.append("job_id", jobId);
  fd.append("filename", filename);
  const res = await fetch(`${BASE}/log-video`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLogs(sessionToken: string): Promise<{ logs: any[]; total_videos: number }> {
  const res = await fetch(`${BASE}/logs/${sessionToken}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
