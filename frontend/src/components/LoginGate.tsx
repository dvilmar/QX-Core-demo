"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { login, verifySession } from "@/lib/api";

export default function LoginGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<"checking" | "locked" | "open">("checking");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    verifySession().then((ok) => setState(ok ? "open" : "locked"));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const failure = await login(username, password);
    setBusy(false);
    if (failure) setError(failure);
    else setState("open");
  }

  if (state === "open") return <>{children}</>;
  if (state === "checking") return null;

  const input =
    "bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent)]";

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <form onSubmit={submit} className="panel p-6 w-full max-w-sm space-y-4">
        <div className="eyebrow">Sign in</div>
        <input className={input} placeholder="Username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input className={input} type="password" placeholder="Password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <div className="text-sm text-[var(--red)]">{error}</div>}
        <button
          type="submit"
          disabled={busy}
          className="w-full bg-[var(--accent-bg)] text-[var(--accent-strong)] border border-[var(--accent)]/30 rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
