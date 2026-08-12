import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Algo Trading Dashboard (Demo)",
  description: "Full-stack demo: FastAPI + Next.js dashboard for a systematic trading strategy, backed by synthetic data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
