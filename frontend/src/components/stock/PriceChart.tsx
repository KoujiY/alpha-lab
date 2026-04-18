import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  createChart,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import type { DailyPricePoint } from "@/api/types";

interface PriceChartProps {
  points: DailyPricePoint[];
}

const MIN_CANDLE_COUNT = 10;

export function PriceChart({ points }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || points.length === 0) return;

    // autoSize 會監聽 container ResizeObserver 並自動套 width/height；
    // 不再另外傳 width/height 初始值，避免重複設定且在 container 初始 0 尺寸時爆警告。
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: false },
      autoSize: true,
    });
    chartRef.current = chart;

    const sorted = [...points].sort((a, b) =>
      a.trade_date.localeCompare(b.trade_date),
    );

    if (sorted.length < MIN_CANDLE_COUNT) {
      const lineData = sorted.map((p) => ({
        time: p.trade_date as Time,
        value: p.close,
      }));
      const lineSeries = chart.addSeries(LineSeries, {
        color: "#38bdf8",
        lineWidth: 2,
      });
      lineSeries.setData(lineData);
    } else {
      const candleData = sorted.map((p) => ({
        time: p.trade_date as Time,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      }));
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#ef4444",
        downColor: "#10b981",
        borderVisible: false,
        wickUpColor: "#ef4444",
        wickDownColor: "#10b981",
      });
      candleSeries.setData(candleData);

      const volumeData = sorted.map((p) => ({
        time: p.trade_date as Time,
        value: p.volume,
        color: p.close >= p.open ? "#ef444480" : "#10b98180",
      }));
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.75, bottom: 0 },
      });
      volumeSeries.setData(volumeData);
    }

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [points]);

  if (points.length === 0) {
    return (
      <section aria-label="股價走勢">
        <h2 className="text-xl font-semibold mb-3">股價走勢</h2>
        <div className="h-64 flex items-center justify-center text-slate-500">
          尚無股價資料
        </div>
      </section>
    );
  }

  return (
    <section aria-label="股價走勢">
      <h2 className="text-xl font-semibold mb-3">股價走勢</h2>
      <div
        ref={containerRef}
        className="h-64 w-full"
        data-testid="price-chart"
      />
    </section>
  );
}
