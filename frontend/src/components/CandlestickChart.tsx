"use client";

import { useEffect, useRef } from "react";
import { createChart, CandlestickSeries, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import type { Candle } from "@/lib/api";

export default function CandlestickChart({ candles }: { candles: Candle[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#948a76",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#221d16" },
        horzLines: { color: "#221d16" },
      },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#221d16" },
      rightPriceScale: { borderColor: "#221d16" },
      height: 360,
      autoSize: true,
    });
    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#3ecf8e",
      downColor: "#ef6a5c",
      borderVisible: false,
      wickUpColor: "#3ecf8e",
      wickDownColor: "#ef6a5c",
    });

    series.setData(
      candles.map((c) => ({
        time: (new Date(c.ts).getTime() / 1000) as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles.length]);

  return <div ref={containerRef} className="w-full" />;
}
