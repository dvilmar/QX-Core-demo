"use client";

import { useEffect, useRef } from "react";
import { createChart, AreaSeries, type IChartApi, type UTCTimestamp } from "lightweight-charts";

export default function EquityChart({ values, timestamps }: { values: number[]; timestamps: string[] }) {
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
      height: 260,
      autoSize: true,
    });
    chartRef.current = chart;

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#d9a54a",
      topColor: "rgba(217, 165, 74, 0.30)",
      bottomColor: "rgba(217, 165, 74, 0.02)",
      lineWidth: 2,
    });

    series.setData(
      values.map((v, i) => ({
        time: (new Date(timestamps[i]).getTime() / 1000) as UTCTimestamp,
        value: v,
      }))
    );
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values.length]);

  return <div ref={containerRef} className="w-full" />;
}
