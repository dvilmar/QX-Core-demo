export default function StatusBar({ connected, lastPrice }: { connected: boolean; lastPrice: number | null }) {
  return (
    <div className="flex items-center justify-between bg-[var(--bg-card)] border border-[var(--border)] rounded-lg px-4 py-2.5">
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${connected ? "bg-[var(--green)] pulse-dot" : "bg-[var(--red)]"}`}
        />
        <span className="text-xs text-[var(--text-dim)]">{connected ? "Live" : "Disconnected"}</span>
      </div>
      <div className="text-sm font-medium tabular-nums">
        {lastPrice !== null ? `$${lastPrice.toFixed(2)}` : "—"}
      </div>
    </div>
  );
}
