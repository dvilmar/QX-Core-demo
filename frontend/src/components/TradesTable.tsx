import type { Trade } from "@/lib/api";

export default function TradesTable({ trades }: { trades: Trade[] }) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
      <div className="text-xs uppercase tracking-widest text-[var(--text-dim)] font-medium mb-3">
        Recent Trades
      </div>
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
              <tr key={i} className="border-b border-[var(--border)]/40">
                <td className="py-2 pr-3 text-[var(--text-dim)] tabular-nums">
                  {new Date(t.entry_ts).toLocaleString()}
                </td>
                <td className="py-2 pr-3 text-[var(--text-dim)] tabular-nums">
                  {new Date(t.exit_ts).toLocaleString()}
                </td>
                <td className="py-2 pr-3">{t.side}</td>
                <td className="py-2 pr-3 text-right tabular-nums">${t.entry_price.toFixed(2)}</td>
                <td className="py-2 pr-3 text-right tabular-nums">${t.exit_price.toFixed(2)}</td>
                <td
                  className={`py-2 pr-0 text-right tabular-nums font-medium ${
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
