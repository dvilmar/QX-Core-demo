"use client";

import { useEffect, useRef } from "react";
import { createChart, AreaSeries, type IChartApi, type UTCTimestamp } from "lightweight-charts";

export default function EquityChart({ values, timestamps }: { values: number[]; timestamps: string[] }) {
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
      height: 260,
      autoSize: true,
    });
    chartRef.current = chart;

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#00b894",
      topColor: "rgba(0, 184, 148, 0.28)",
      bottomColor: "rgba(0, 184, 148, 0.02)",
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
