import type { Trade } from "@/lib/api";

function SideBadge({ side }: { side: string }) {
  const long = side.toUpperCase() === "LONG";
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold tracking-wide ${
        long ? "bg-[var(--green-bg)] text-[var(--green)]" : "bg-[var(--red-bg)] text-[var(--red)]"
      }`}
    >
      {side.toUpperCase()}
    </span>
  );
}

export default function TradesTable({ trades }: { trades: Trade[] }) {
  return (
    <div className="panel p-4">
      <div className="eyebrow mb-3">Recent Trades</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[var(--text-muted)] text-[11px] uppercase tracking-wider border-b border-[var(--border)]">
              <th className="py-2 pr-3 font-medium">Entry</th>
              <th className="py-2 pr-3 font-medium">Exit</th>
              <th className="py-2 pr-3 font-medium">Side</th>
              <th className="py-2 pr-3 font-medium text-right">Entry Px</th>
              <th className="py-2 pr-3 font-medium text-right">Exit Px</th>
              <th className="py-2 pr-0 font-medium text-right">PnL</th>
            </tr>
          </thead>
          <tbody>
            {[...trades].reverse().map((t, i) => (
              <tr key={i} className="border-b border-[var(--border)]/60 hover:bg-[var(--bg-card-hover)] transition-colors">
                <td className="py-2 pr-3 text-[var(--text-dim)] tabular-nums text-xs">
                  {new Date(t.entry_ts).toLocaleString()}
                </td>
                <td className="py-2 pr-3 text-[var(--text-dim)] tabular-nums text-xs">
                  {new Date(t.exit_ts).toLocaleString()}
                </td>
                <td className="py-2 pr-3">
                  <SideBadge side={t.side} />
                </td>
                <td className="py-2 pr-3 text-right tabular-nums">${t.entry_price.toFixed(2)}</td>
                <td className="py-2 pr-3 text-right tabular-nums">${t.exit_price.toFixed(2)}</td>
                <td
                  className={`py-2 pr-0 text-right tabular-nums font-semibold ${
                    t.pnl >= 0 ? "text-[var(--green)]" : "text-[var(--red)]"
                  }`}
                >
                  {t.pnl >= 0 ? "+" : ""}
                  {t.pnl.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {trades.length === 0 && (
          <div className="text-center text-[var(--text-muted)] text-sm py-6">No trades yet.</div>
        )}
      </div>
    </div>
  );
}
