type Tone = "neutral" | "green" | "red" | "yellow";

const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-[var(--text)]",
  green: "text-[var(--green)]",
  red: "text-[var(--red)]",
  yellow: "text-[var(--accent-strong)]",
};

const TONE_STRIPE: Record<Tone, string> = {
  neutral: "bg-[var(--border-hover)]",
  green: "bg-[var(--green)]",
  red: "bg-[var(--red)]",
  yellow: "bg-[var(--accent)]",
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
    <div className="panel relative overflow-hidden p-4 transition-colors">
      <span className={`absolute left-0 top-0 h-full w-[3px] ${TONE_STRIPE[tone]}`} />
      <div className="eyebrow mb-2">{label}</div>
      <div className={`font-mono text-2xl font-medium tabular-nums ${TONE_TEXT[tone]}`}>{value}</div>
      {sub && <div className="text-xs text-[var(--text-muted)] mt-1.5">{sub}</div>}
    </div>
  );
}
