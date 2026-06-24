import { useCallback, useState, useEffect } from "react";
import LoginPage from "./components/LoginPage";
import UploadZone  from "./components/UploadZone";
import ProgressBar from "./components/ProgressBar";
import VideoLogs from "./components/VideoLogs";
import { useCounter } from "./hooks/useCounter";

// Colour tokens matching the Python annotation palette
const LABEL_COLORS: Record<string, string> = {
  Box:    "#ffa01e",
  Packet: "#50dc78",
  Parcel: "#50a0ff",
};

interface StatCardProps {
  label: string;
  value: number;
  accent: string;
  sub?: string;
}

function StatCard({ label, value, accent, sub }: StatCardProps) {
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-1 relative overflow-hidden"
      style={{ background: `color-mix(in srgb, ${accent} 12%, #0f1117)`, border: `1px solid color-mix(in srgb, ${accent} 30%, transparent)` }}
    >
      <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: accent }}>
        {label}
      </span>
      <span className="text-5xl font-black tabular-nums text-white leading-none mt-1">{value}</span>
      {sub && <span className="text-xs text-gray-500 mt-1">{sub}</span>}
      {/* subtle glow blob */}
      <div
        className="absolute -bottom-6 -right-6 w-24 h-24 rounded-full blur-2xl opacity-20 pointer-events-none"
        style={{ background: accent }}
      />
    </div>
  );
}

export default function App() {
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);

  // Load session from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("scanconvey_session");
    if (saved) {
      setSessionToken(saved);
    }
  }, []);

  const { phase, counts, progress, frameB64, error, start, reset } = useCounter(sessionToken);

  const handleFile = useCallback((f: File) => { start(f); }, [start]);
  const isActive   = phase === "uploading" || phase === "processing";
  const hasFrame   = !!frameB64;

  const handleLoginSuccess = (token: string, _userId: string) => {
    setSessionToken(token);
    localStorage.setItem("scanconvey_session", token);
  };

  const handleLogout = () => {
    setSessionToken(null);
    localStorage.removeItem("scanconvey_session");
    reset();
  };

  if (!sessionToken) {
    return <LoginPage onSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-[#0a0c10] text-gray-100 flex flex-col font-sans">

      {/* Header */}
      <header className="border-b border-gray-800/60 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* ScanConvey Logo */}
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 text-white" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="8" width="18" height="8" rx="2" />
              <circle cx="7" cy="12" r="1.5" fill="currentColor" stroke="none" />
              <circle cx="17" cy="12" r="1.5" fill="currentColor" stroke="none" />
              <path d="M7 16v2M17 16v2" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">ScanConvey</h1>
            <p className="text-[10px] text-gray-500 mt-0.5">Smart Conveyor Detection System</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="text-xs px-3 py-1.5 rounded-lg bg-gray-800/60 hover:bg-gray-700 text-gray-300 transition-colors border border-gray-700 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Logs
          </button>

          {(phase === "processing" || phase === "done") && (
            <button
              onClick={reset}
              className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors border border-gray-700"
            >
              New video
            </button>
          )}

          <button
            onClick={handleLogout}
            className="text-xs px-3 py-1.5 rounded-lg bg-red-900/40 hover:bg-red-900/60 text-red-300 transition-colors border border-red-700/60"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8 space-y-6">

        {/* Logs Sidebar */}
        {showLogs && (
          <div className="rounded-2xl bg-gray-900/60 border border-gray-800/60 p-6">
            <VideoLogs sessionToken={sessionToken} />
          </div>
        )}

        {/* ── IDLE / ERROR ─────────────────────────────────────────── */}
        {(phase === "idle" || phase === "error") && (
          <div className="space-y-5">
            <UploadZone onFile={handleFile} disabled={isActive} />
            {error && (
              <div className="rounded-xl bg-red-950/40 border border-red-800/60 p-4 text-sm text-red-300">
                <span className="font-semibold text-red-400">Error: </span>{error}
              </div>
            )}

            {/* How it works */}
            <div className="rounded-2xl bg-gray-900/60 border border-gray-800/60 p-6">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">How it works</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  ["Belt Region Detection", "Auto-detects conveyor belt area to count only valid objects"],
                  ["MOG2 Background Subtraction", "Adaptive foreground mask with shadow removal"],
                  ["Morphological Pipeline", "OPEN + DILATE to clean noise and merge blobs"],
                  ["Centroid Tracker", "Nearest-neighbour tracker assigns persistent IDs"],
                  ["YOLOv8-nano", "Defect scan every 10 frames — crack / misalignment"],
                  ["Video History Log", "Automatic logging of all video processing results"],
                ].map(([title, desc]) => (
                  <div key={title} className="flex gap-3 items-start p-3 rounded-xl bg-gray-800/40 border border-gray-700/30">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 mt-1.5 flex-shrink-0" />
                    <div>
                      <p className="text-xs font-semibold text-gray-200">{title}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── UPLOADING ────────────────────────────────────────────── */}
        {phase === "uploading" && (
          <div className="flex flex-col items-center gap-4 py-20">
            <div className="w-10 h-10 rounded-full border-4 border-cyan-500 border-t-transparent animate-spin" />
            <p className="text-gray-400 text-sm">Uploading video...</p>
          </div>
        )}

        {/* ── PROCESSING / DONE ────────────────────────────────────── */}
        {(phase === "processing" || phase === "done") && (
          <div className="space-y-5">

            {/* Emergency halt banner */}
            {counts.halt && (
              <div className="rounded-xl bg-red-950/50 border border-red-700 p-4 text-sm text-red-300 flex gap-3 items-start">
                <div className="w-2 h-2 rounded-full bg-red-500 mt-1 flex-shrink-0 animate-pulse" />
                <div>
                  <span className="font-bold text-red-400">Emergency Line Halt — </span>
                  {counts.haltReason}
                </div>
              </div>
            )}

            {/* Stat cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard label="Total Packets" value={counts.packets} accent="#818cf8" />
              <StatCard label="Functional"    value={counts.boxes}   accent="#50dc78" />
              <StatCard label="Defective"     value={counts.defects} accent="#f87171" />
            </div>

            {/* Live frame viewer */}
            <div className="rounded-2xl overflow-hidden border border-gray-800/60 bg-gray-900/50 relative">
              {/* Header bar */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800/60 bg-gray-900/80">
                <div className="flex items-center gap-2">
                  {phase === "processing" && (
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  )}
                  {phase === "done" && (
                    <span className="w-2.5 h-2.5 rounded-full bg-gray-500" />
                  )}
                  <span className="text-xs font-medium text-gray-300">
                    {phase === "processing" ? "Live detection feed" : "Last processed frame"}
                  </span>
                </div>
              </div>

              {/* Frame image */}
              <div className="relative bg-black min-h-[200px] flex items-center justify-center">
                {hasFrame ? (
                  <img
                    src={`data:image/jpeg;base64,${frameB64}`}
                    alt="Annotated detection frame"
                    className="w-full object-contain max-h-[540px]"
                    style={{ imageRendering: "auto" }}
                  />
                ) : (
                  <div className="flex flex-col items-center gap-3 py-16 text-gray-600">
                    <div className="w-8 h-8 rounded-full border-2 border-gray-700 border-t-cyan-500 animate-spin" />
                    <span className="text-sm">Waiting for first frame...</span>
                  </div>
                )}

                {/* Counting line label overlay */}
                {hasFrame && phase === "processing" && (
                  <div className="absolute bottom-3 right-3 bg-black/60 rounded-lg px-3 py-1.5 text-[11px] text-cyan-400 font-mono border border-cyan-900/60">
                    frame {progress.frame.toLocaleString()} / {progress.total.toLocaleString()}
                  </div>
                )}
              </div>

              {/* Progress bar */}
              {phase === "processing" && (
                <div className="px-4 py-3 border-t border-gray-800/60 bg-gray-900/60">
                  <ProgressBar
                    progress={progress.progress}
                    frame={progress.frame}
                    total={progress.total}
                  />
                </div>
              )}
            </div>

            {/* Done state */}
            {phase === "done" && (
              <div className="rounded-2xl bg-emerald-950/40 border border-emerald-800/50 p-5 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-emerald-400">Detection complete</p>
                  <p className="text-sm text-gray-400 mt-0.5">
                    Found <span className="text-white font-bold">{counts.total}</span> items
                    {counts.defects > 0 && (
                      <span className="text-red-400"> — {counts.defects} defect(s) flagged</span>
                    )}
                  </p>
                </div>
                <button
                  onClick={reset}
                  className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium transition-colors"
                >
                  Analyse another
                </button>
              </div>
            )}

          </div>
        )}
      </main>

      <footer className="border-t border-gray-800/40 py-3 text-center text-[11px] text-gray-700">
        ScanConvey · Secuodsoft Technologies Internship
      </footer>
    </div>
  );
}
