import { useEffect, useState } from "react";

interface VideoLog {
  id: number;
  filename: string;
  boxes: number;
  packets: number;
  parcels: number;
  total: number;
  defects: number;
  started_at: string;
  finished_at: string;
}

interface VideoLogsProps {
  sessionToken: string;
}

export default function VideoLogs({ sessionToken }: VideoLogsProps) {
  const [logs, setLogs] = useState<VideoLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch(`${API_URL}/logs/${sessionToken}`);
        const data = await res.json();
        if (res.ok) {
          setLogs(data.logs);
        } else {
          setError("Failed to load logs");
        }
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [sessionToken]);

  const formatDate = (isoString: string) => {
    return new Date(isoString).toLocaleString();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Video History</h2>
        <span className="text-xs text-gray-500">{logs.length} videos processed</span>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-950/40 border border-red-800/60 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {!loading && logs.length === 0 && (
        <div className="rounded-lg bg-gray-900/50 border border-gray-800/60 p-8 text-center">
          <p className="text-gray-500 text-sm">No videos processed yet</p>
        </div>
      )}

      {!loading && logs.length > 0 && (
        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-xl bg-gray-900/60 border border-gray-800/60 p-4 space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-sm text-cyan-400 truncate">
                    {log.filename}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {formatDate(log.started_at)}
                  </p>
                </div>
                <span className="px-2 py-1 bg-blue-900/40 border border-blue-700/60 rounded text-xs font-mono text-blue-300">
                  {log.total} items
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg bg-indigo-900/30 border border-indigo-700/30 p-2 text-center">
                  <p className="text-xs text-indigo-400 font-semibold">{log.packets}</p>
                  <p className="text-[10px] text-indigo-600">Total Packets</p>
                </div>
                <div className="rounded-lg bg-green-900/30 border border-green-700/30 p-2 text-center">
                  <p className="text-xs text-green-400 font-semibold">{log.boxes}</p>
                  <p className="text-[10px] text-green-600">Functional</p>
                </div>
                <div className="rounded-lg bg-red-900/30 border border-red-700/30 p-2 text-center">
                  <p className="text-xs text-red-400 font-semibold">{log.defects}</p>
                  <p className="text-[10px] text-red-600">Defective</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
