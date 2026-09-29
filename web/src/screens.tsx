import { CandlestickSeries, ColorType, createChart, type CandlestickData, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./api";
import { applyDirection } from "./i18n";

type Dash = {
  broker: { balance: number; equity: number; killed: boolean };
  market_state: string;
  mode: string;
  provider: string;
  runtime: string;
  model: string;
  agent: string;
  status: string;
  tools: string[];
  freshness: string | null;
  source: string;
};

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4 shadow-[var(--shadow)]">
      <div className="text-xs text-[var(--muted)]">{title}</div>
      <div className="mt-1 break-all text-lg">{value}</div>
    </div>
  );
}

export function Dashboard() {
  const { t } = useTranslation();
  const [data, setData] = useState<Dash | null>(null);
  const [note, setNote] = useState("");
  async function load() {
    setData(await api<Dash>("/api/dashboard"));
  }
  useEffect(() => { void load(); }, []);
  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button className="rounded-lg bg-[var(--gold)] px-3 py-2 text-sm text-black" onClick={async () => { await api("/api/market/replay/synthetic", { method: "POST" }); setNote("SIMULATOR"); await load(); }}>{t("loadReplay")}</button>
        <button className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm" onClick={async () => { await api("/api/cycle", { method: "POST" }); await load(); }}>{t("runCycle")}</button>
        <button className="rounded-lg bg-[var(--danger)] px-3 py-2 text-sm text-white" onClick={async () => { await api("/api/broker/kill", { method: "POST" }); await load(); }}>{t("kill")}</button>
      </div>
      {note && <p className="mb-3 text-sm text-[var(--gold)]">{note}</p>}
      {!data ? <p>{t("empty")}</p> : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Card title={t("balance")} value={String(data.broker.balance)} />
          <Card title={t("equity")} value={String(data.broker.equity)} />
          <Card title={t("market")} value={data.market_state} />
          <Card title={t("mode")} value={data.mode === "paper" ? t("paper") : t("live")} />
          <Card title={t("agent")} value={data.agent} />
          <Card title={t("provider")} value={data.provider} />
          <Card title={t("model")} value={data.model} />
          <Card title={t("runtime")} value={data.runtime} />
          <Card title={t("status")} value={data.status} />
          <Card title={t("tools")} value={data.tools.length ? data.tools.join(", ") : "—"} />
          <Card title={t("freshness")} value={data.freshness ? data.freshness.slice(0, 16).replace("T", " ") : data.source} />
        </div>
      )}
    </section>
  );
}

type ChatReply = {
  text: string;
  provider: string;
  model: string;
  runtime: string;
  agent: string;
  status: string;
  tools: string[];
};

export function Chat() {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const [lines, setLines] = useState<{ role: string; body: string; meta?: ChatReply }[]>([]);
  return (
    <section className="mx-auto max-w-3xl">
      <div className="mb-3 space-y-2">
        {lines.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
        {lines.map((line, index) => (
          <div key={index} className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-3 text-sm">
            {line.meta && (
              <div className="mb-2 text-xs text-[var(--muted)]">
                <div>{line.meta.agent}</div>
                <div>{line.meta.provider}</div>
                <div>{line.meta.model}</div>
                <div>{line.meta.runtime}</div>
                <div>● {line.meta.status}</div>
                <div>{t("tools")}: {line.meta.tools.join(", ") || "—"}</div>
              </div>
            )}
            {line.body}
          </div>
        ))}
      </div>
      <form className="flex gap-2" onSubmit={async (event) => {
        event.preventDefault();
        const message = text;
        setText("");
        setLines((current) => [...current, { role: "user", body: message }]);
        const reply = await api<ChatReply>("/api/chat", { method: "POST", body: JSON.stringify({ message }) });
        setLines((current) => [...current, { role: "mokli", body: reply.text, meta: reply }]);
      }}>
        <input className="flex-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2" value={text} onChange={(event) => setText(event.target.value)} />
        <button className="rounded-lg bg-[var(--gold)] px-3 py-2 text-black" type="submit">{t("send")}</button>
      </form>
    </section>
  );
}

export function Activity() {
  return <JsonView path="/api/activity" />;
}
export function Agents() {
  return <JsonView path="/api/agents/tree" />;
}
export function Debate() {
  const { t } = useTranslation();
  const [notes, setNotes] = useState<{ role: string; text: string }[]>([]);
  return (
    <section>
      <button className="mb-3 rounded-lg bg-[var(--gold)] px-3 py-2 text-sm text-black" onClick={async () => {
        const cycle = await api<{ notes: { role: string; text: string }[] }>("/api/cycle", { method: "POST" });
        setNotes(cycle.notes || []);
      }}>{t("runCycle")}</button>
      {notes.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        {notes.map((note) => (
          <article key={note.role} className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4">
            <h3 className="mb-1 text-[var(--gold)]">{note.role}</h3>
            <p className="text-sm">{note.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ChartPage() {
  const ref = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  useEffect(() => {
    if (!ref.current) return;
    let chart: IChartApi | null = null;
    let series: ISeriesApi<"Candlestick"> | null = null;
    let dead = false;
    void (async () => {
      const payload = await api<{ candles: { time: string; open: number; high: number; low: number; close: number }[] }>("/api/market/candles");
      if (dead || !ref.current) return;
      chart = createChart(ref.current, {
        height: 420,
        localization: { locale: "en-US" },
        layout: { background: { type: ColorType.Solid, color: "#12161d" }, textColor: "#ece8e1" },
        grid: { vertLines: { color: "#2c3444" }, horzLines: { color: "#2c3444" } },
      });
      series = chart.addSeries(CandlestickSeries, { upColor: "#2fbf8a", downColor: "#e15d66", borderVisible: false, wickUpColor: "#2fbf8a", wickDownColor: "#e15d66" });
      const rows: CandlestickData[] = payload.candles.map((candle) => ({
        time: Math.floor(new Date(candle.time).getTime() / 1000) as CandlestickData["time"],
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }));
      if (!series) return;
      series.setData(rows);
      chart.timeScale().fitContent();
    })();
    return () => { dead = true; chart?.remove(); };
  }, []);
  return (
    <section>
      <p className="mb-2 text-sm text-[var(--muted)]">{t("nav.charts")}</p>
      <div ref={ref} dir="ltr" className="chart-ltr rounded-[var(--radius)] border border-[var(--line)]" />
    </section>
  );
}

export function Signals() {
  return <JsonView path="/api/journal" />;
}
export function Approvals() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<{ id: string; payload: { side?: string; entry?: number } }[]>([]);
  async function load() {
    const body = await api<{ approvals: { id: string; payload: { side?: string; entry?: number } }[] }>("/api/approvals");
    setRows(body.approvals);
  }
  useEffect(() => { void load(); }, []);
  return (
    <section className="space-y-3">
      {rows.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
      {rows.map((row) => (
        <article key={row.id} className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4">
          <p>{row.payload.side} @ {row.payload.entry}</p>
          <div className="mt-2 flex gap-2">
            <button className="rounded-lg bg-[var(--buy)] px-3 py-1 text-sm text-black" onClick={async () => { await api(`/api/approvals/${row.id}/approve`, { method: "POST" }); await load(); }}>{t("approve")}</button>
            <button className="rounded-lg bg-[var(--sell)] px-3 py-1 text-sm" onClick={async () => { await api(`/api/approvals/${row.id}/reject`, { method: "POST" }); await load(); }}>{t("reject")}</button>
          </div>
        </article>
      ))}
    </section>
  );
}
export function Skills() {
  const [rows, setRows] = useState<{ name: string; description: string; enabled: boolean }[]>([]);
  async function load() {
    setRows((await api<{ skills: { name: string; description: string; enabled: boolean }[] }>("/api/skills")).skills);
  }
  useEffect(() => { void load(); }, []);
  return (
    <section className="space-y-3">
      {rows.map((row) => (
        <button key={row.name} className="block w-full rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4 text-start" onClick={async () => { await api(`/api/skills/${row.name}/toggle`, { method: "POST" }); await load(); }}>
          <div className="text-[var(--gold)]">{row.name}</div>
          <div className="text-sm text-[var(--muted)]">{row.description}</div>
          <div className="text-xs">{row.enabled ? "on" : "off"}</div>
        </button>
      ))}
    </section>
  );
}
export function Rules() {
  const { i18n } = useTranslation();
  const [rows, setRows] = useState<{ id: string; title_en: string; title_ar: string; type: string; enabled: boolean }[]>([]);
  async function load() {
    setRows((await api<{ rules: { id: string; title_en: string; title_ar: string; type: string; enabled: boolean }[] }>("/api/rules")).rules);
  }
  useEffect(() => { void load(); }, []);
  const guardrails = rows.filter((row) => row.type === "guardrail");
  return (
    <section className="space-y-2">
      {guardrails.map((row) => (
        <button key={row.id} className="block w-full rounded-lg border border-[var(--line)] bg-[var(--card)] p-3 text-start text-sm" onClick={async () => { await api(`/api/rules/${row.id}/toggle`, { method: "POST" }); await load(); }}>
          <span className="text-[var(--gold)]">{row.id}</span> {i18n.language === "ar" ? row.title_ar : row.title_en}
          <span className="ms-2 text-xs text-[var(--muted)]">{row.enabled ? "on" : "off"}</span>
        </button>
      ))}
    </section>
  );
}
export function News() { return <JsonView path="/api/news" />; }
export function Journal() { return <JsonView path="/api/journal" />; }
export function Lessons() { return <JsonView path="/api/lessons" />; }
export function Reports() { return <JsonView path="/api/reports/daily" />; }

export function Settings() {
  const { t, i18n } = useTranslation();
  const [live, setLive] = useState(false);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  useEffect(() => {
    void api<{ live_confirmed: boolean; capabilities: string[] }>("/api/settings").then((body) => {
      setLive(body.live_confirmed);
      setCapabilities(body.capabilities);
    });
  }, []);
  return (
    <section className="max-w-lg space-y-4">
      <div className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4 text-sm">
        <div className="mb-2 text-[var(--muted)]">{t("runtime")}</div>
        <div>{capabilities.join(" · ") || "—"}</div>
      </div>
      <label className="block text-sm">{t("language")}</label>
      <select className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2" value={i18n.language} onChange={async (event) => {
        const language = event.target.value;
        await i18n.changeLanguage(language);
        applyDirection(language);
        await api("/api/settings", { method: "PUT", body: JSON.stringify({ language }) });
      }}>
        <option value="ar">العربية</option>
        <option value="en">English</option>
      </select>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={live} onChange={async (event) => {
          setLive(event.target.checked);
          await api("/api/settings", { method: "PUT", body: JSON.stringify({ live_confirmed: event.target.checked }) });
        }} />
        {t("live")}
      </label>
      <p className="text-xs text-[var(--muted)]">MOKLI_LIVE=1 is still required. Confirmation alone does not leave paper.</p>
    </section>
  );
}

function JsonView({ path }: { path: string }) {
  const { t } = useTranslation();
  const [body, setBody] = useState<unknown>(null);
  useEffect(() => { void api(path).then(setBody); }, [path]);
  if (!body) return <p className="text-[var(--muted)]">{t("empty")}</p>;
  return <pre className="overflow-auto rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4 text-xs">{JSON.stringify(body, null, 2)}</pre>;
}
