import { useState, useRef, useCallback } from "react";
import { uploadVideo, openEventStream, logVideo } from "../api/api";

export type Phase = "idle" | "uploading" | "processing" | "done" | "error";

export interface CountState {
  boxes:      number;
  packets:    number;
  parcels:    number;
  total:      number;
  defects:    number;
  halt:       boolean;
  haltReason: string;
}

export interface JobProgress {
  frame:    number;
  total:    number;
  progress: number;
}

export function useCounter(sessionToken: string | null) {
  const [phase,      setPhase]      = useState<Phase>("idle");
  const [counts,     setCounts]     = useState<CountState>({
    boxes: 0, packets: 0, parcels: 0, total: 0, defects: 0, halt: false, haltReason: "",
  });
  const [progress,   setProgress]   = useState<JobProgress>({ frame: 0, total: 0, progress: 0 });
  const [frameB64,   setFrameB64]   = useState<string | null>(null);
  const [error,      setError]      = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const jobIdRef = useRef<string>("");
  const fileNameRef = useRef<string>("");

  const start = useCallback(async (file: File) => {
    if (!sessionToken) {
      setError("Not authenticated");
      setPhase("error");
      return;
    }

    setPhase("uploading");
    setError(null);
    setFrameB64(null);
    setCounts({ boxes: 0, packets: 0, parcels: 0, total: 0, defects: 0, halt: false, haltReason: "" });
    setProgress({ frame: 0, total: 0, progress: 0 });

    try {
      const { job_id, total_frames } = await uploadVideo(file, sessionToken);
      jobIdRef.current = job_id;
      fileNameRef.current = file.name;
      setPhase("processing");
      setProgress(p => ({ ...p, total: total_frames }));

      const es = openEventStream(job_id);
      esRef.current = es;

      es.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);

          if (data.type === "progress") {
            setProgress({ frame: data.frame, total: data.total, progress: data.progress });
            setCounts({
              boxes:      data.boxes,
              packets:    data.packets,
              parcels:    data.parcels,
              total:      data.boxes + data.packets + data.parcels,
              defects:    data.defects ?? 0,
              halt:       data.halt ?? false,
              haltReason: data.halt_reason ?? "",
            });
            if (data.frame_b64) setFrameB64(data.frame_b64);
          }

          if (data.type === "done") {
            setCounts({
              boxes:      data.boxes,
              packets:    data.packets,
              parcels:    data.parcels,
              total:      data.total,
              defects:    data.defects ?? 0,
              halt:       data.halt ?? false,
              haltReason: data.halt_reason ?? "",
            });
            setPhase("done");
            es.close();

            // Log video after processing
            if (sessionToken && jobIdRef.current) {
              logVideo(sessionToken, jobIdRef.current, fileNameRef.current).catch(console.error);
            }
          }

          if (data.type === "error") {
            setError(data.message);
            setPhase("error");
            es.close();
          }
        } catch { /* ignore malformed */ }
      };

      es.onerror = () => {
        if (esRef.current?.readyState === EventSource.CLOSED) {
          esRef.current = null;
        }
      };

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    }
  }, [sessionToken]);

  const reset = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setPhase("idle");
    setCounts({ boxes: 0, packets: 0, parcels: 0, total: 0, defects: 0, halt: false, haltReason: "" });
    setProgress({ frame: 0, total: 0, progress: 0 });
    setFrameB64(null);
    setError(null);
  }, []);

  return { phase, counts, progress, frameB64, error, start, reset };
}
