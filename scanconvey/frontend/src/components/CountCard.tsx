interface Props {
  label:   string;
  value:   number;
  color:   string;
  bgColor: string;
}

export default function CountCard({ label, value, color, bgColor }: Props) {
  return (
    <div className={`rounded-2xl p-6 flex flex-col gap-3 ${bgColor}`}>
      <span className="text-sm font-medium text-gray-400">{label}</span>
      <span className={`text-5xl font-bold tabular-nums ${color}`}>{value}</span>
    </div>
  );
}
