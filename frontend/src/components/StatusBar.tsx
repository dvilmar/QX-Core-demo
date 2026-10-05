export default function StatusBar({ connected, lastPrice }: { connected: boolean; lastPrice: number | null }) {
  return (
    <div className="panel flex items-center justify-between px-4 py-2.5">
      <div className="flex items-center gap-2.5">
        <span className="relative flex h-2 w-2">
          <span
            className={`absolute inline-flex h-full w-full rounded-full ${
              connected ? "bg-[var(--green)] pulse-dot" : "bg-[var(--red)]"
            }`}
          />
        </span>
        <span className="eyebrow">{connected ? "Live" : "Disconnected"}</span>
      </div>
      <div className="font-mono text-sm font-medium tabular-nums text-[var(--text)]">
        {lastPrice !== null ? `$${lastPrice.toFixed(2)}` : "—"}
      </div>
    </div>
  );
}
