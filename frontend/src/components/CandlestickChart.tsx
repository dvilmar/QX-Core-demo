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
      layout: { background: { color: "#141414" }, textColor: "#a0a0a0" },
      grid: {
        vertLines: { color: "#1e1e1e" },
        horzLines: { color: "#1e1e1e" },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
      height: 360,
      autoSize: true,
    });
    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#00b894",
      downColor: "#ff6b6b",
      borderVisible: false,
      wickUpColor: "#00b894",
      wickDownColor: "#ff6b6b",
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
    // re-create the chart whenever the candle set changes length (new backtest run etc.)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles.length]);

  return <div ref={containerRef} className="w-full" />;
}
