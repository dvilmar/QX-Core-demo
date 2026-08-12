type Tone = "neutral" | "green" | "red" | "yellow";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "text-[#e8e8e8]",
  green: "text-[var(--green)]",
  red: "text-[var(--red)]",
  yellow: "text-[var(--yellow)]",
};

export default function Kpi({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
}) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
      <div className="text-[11px] uppercase tracking-widest text-[var(--text-dim)] font-medium mb-1.5">
        {label}
      </div>
      <div className={`text-2xl font-semibold tabular-nums ${TONE_CLASSES[tone]}`}>{value}</div>
      {sub && <div className="text-xs text-[var(--text-muted)] mt-1">{sub}</div>}
    </div>
  );
}
