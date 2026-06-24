import { useRef, useState, DragEvent } from "react";

interface Props {
  onFile: (f: File) => void;
  disabled?: boolean;
}

export default function UploadZone({ onFile, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFile = (f: File | undefined) => {
    if (!f || disabled) return;
    onFile(f);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`
        relative flex flex-col items-center justify-center gap-4
        rounded-2xl border-2 border-dashed cursor-pointer select-none
        transition-all duration-200 py-16 px-8
        ${dragging
          ? "border-brand bg-brand/10"
          : "border-gray-600 hover:border-brand/60 hover:bg-gray-800/50"}
        ${disabled ? "opacity-40 cursor-not-allowed" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
        disabled={disabled}
      />

      {/* icon */}
      <div className="w-16 h-16 rounded-full bg-brand/20 flex items-center justify-center">
        <svg className="w-8 h-8 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
      </div>

      <div className="text-center">
        <p className="text-base font-medium text-gray-200">
          Drop a conveyor video here
        </p>
        <p className="text-sm text-gray-500 mt-1">
          or click to browse &middot; MP4, AVI, MOV, MKV
        </p>
      </div>
    </div>
  );
}
