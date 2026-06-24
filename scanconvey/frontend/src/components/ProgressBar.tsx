interface Props {
  progress: number;   // 0–100
  frame:    number;
  total:    number;
}

export default function ProgressBar({ progress, frame, total }: Props) {
  const pct = Math.min(100, Math.max(0, progress));
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-xs text-gray-400">
        <span>Processing frames…</span>
        <span>{frame.toLocaleString()} / {total.toLocaleString()} &nbsp;({pct.toFixed(1)}%)</span>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2.5 overflow-hidden">
        <div
          className="h-2.5 rounded-full bg-brand transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
