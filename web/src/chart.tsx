import { CandlestickSeries, ColorType, createChart, type CandlestickData, type IChartApi, type Time } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type AxisTick = { label: string; x: number };

function candleStamp(time: Time | number): string {
  const unix = typeof time === "number"
    ? time
    : typeof time === "string"
      ? Math.floor(Date.parse(time) / 1000)
      : Math.floor(Date.UTC(time.year, time.month - 1, time.day) / 1000);
  const date = new Date(unix * 1000);
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hour = String(date.getUTCHours()).padStart(2, "0");
  const minute = String(date.getUTCMinutes()).padStart(2, "0");
  return `${month}-${day} ${hour}:${minute}`;
}

export function InlineChart() {
  const ref = useRef<HTMLDivElement>(null);
  const [ticks, setTicks] = useState<AxisTick[]>([]);
  const [empty, setEmpty] = useState(false);
  useEffect(() => {
    if (!ref.current) return;
    let chart: IChartApi | null = null;
    let dead = false;
    const paint = (apiChart: IChartApi, rows: CandlestickData[]) => {
      const step = Math.max(1, Math.floor((rows.length - 1) / 5));
      const indexes = new Set<number>([0, rows.length - 1]);
      for (let index = 0; index < rows.length; index += step) indexes.add(index);
      const next: AxisTick[] = [];
      for (const index of [...indexes].sort((left, right) => left - right)) {
        const row = rows[index];
        if (!row) continue;
        const x = apiChart.timeScale().timeToCoordinate(row.time);
        const label = candleStamp(row.time as Time);
        if (x == null || next.some((item) => item.label === label)) continue;
        const previous = next[next.length - 1];
        const last = index === rows.length - 1;
        if (previous && x - previous.x < 88) {
          if (last && next.length > 1) next[next.length - 1] = { label, x };
          else if (last) next.push({ label, x });
          continue;
        }
        next.push({ label, x });
      }
      if (!dead) setTicks(next);
    };
    void (async () => {
      const payload = await api<{ candles: { time: string; open: number; high: number; low: number; close: number }[] }>("/api/market/candles");
      if (dead || !ref.current) return;
      if (!payload.candles.length) {
        setEmpty(true);
        return;
      }
      chart = createChart(ref.current, {
        autoSize: true,
        rightPriceScale: { minimumWidth: 72 },
        localization: { locale: "en-US", timeFormatter: (time: Time) => candleStamp(time) },
        timeScale: {
          visible: false,
          borderVisible: false,
          timeVisible: true,
          secondsVisible: false,
          tickMarkMaxCharacterLength: 14,
          tickMarkFormatter: (time: Time) => candleStamp(time),
        },
        layout: { attributionLogo: false, background: { type: ColorType.Solid, color: "#1c1c1e" }, textColor: "#f3f3f4" },
        grid: { vertLines: { color: "#2a2a2c" }, horzLines: { color: "#2a2a2c" } },
      });
      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#2fbf8a",
        downColor: "#e15d66",
        borderVisible: false,
        wickUpColor: "#2fbf8a",
        wickDownColor: "#e15d66",
      });
      const rows: CandlestickData[] = payload.candles.map((candle) => ({
        time: Math.floor(new Date(candle.time).getTime() / 1000) as CandlestickData["time"],
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }));
      series.setData(rows);
      chart.timeScale().fitContent();
      const apiChart = chart;
      const draw = () => paint(apiChart, rows);
      draw();
      requestAnimationFrame(draw);
      window.setTimeout(draw, 250);
      chart.timeScale().subscribeVisibleLogicalRangeChange(draw);
      chart.timeScale().subscribeSizeChange(draw);
    })();
    return () => { dead = true; chart?.remove(); };
  }, []);
  return (
    <div data-inline-chart className="mt-3">
      <p className="mb-2 text-sm text-[var(--muted)]"><span className="latin">XAUUSD</span></p>
      {empty ? <p className="text-sm text-[var(--muted)]">—</p> : (
        <>
          <div ref={ref} dir="ltr" className="chart-ltr inline-chart w-full rounded-[var(--radius)] border border-[var(--line)]" />
          <div dir="ltr" data-chart-axis className="chart-axis">
            {ticks.map((tick) => (
              <span key={tick.label} style={{ left: tick.x, transform: tick.x < 48 ? "none" : "translateX(-50%)" }}>{tick.label}</span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
