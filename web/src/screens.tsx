import { CandlestickSeries, ColorType, createChart, type CandlestickData, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./api";
import { applyDirection } from "./i18n";
import { Notifications, VoicePanel } from "./panels";

export { Activity, Agents, Journal, News, Reports, Signals } from "./panels";

type Book = {
  state: string;
  bid: number | null;
  ask: number | null;
  spread_points: number | null;
  index: number;
  total: number;
  source: string;
};

type Position = { id: string; side: string; remaining: number; entry: number; status: string };

type Dash = {
  broker: { balance: number; equity: number; killed: boolean; positions?: Position[] };
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
  book?: Book;
};

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4 shadow-[var(--shadow)]">
      <div className="text-xs text-[var(--muted)]">{title}</div>
      <div className="mt-1 whitespace-pre-line break-words text-lg leading-snug">{value}</div>
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
  const book = data?.book;
  const open = (data?.broker.positions || []).filter((item) => item.status === "open");
  return (
    <section className="space-y-4">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button className="rounded-lg bg-[var(--gold)] px-3 py-2 text-sm text-black" onClick={async () => { await api("/api/market/replay/synthetic", { method: "POST" }); setNote("SIMULATOR"); await load(); }}>{t("loadReplay")}</button>
        <button className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm" onClick={async () => { try { await api("/api/market/replay/arm?start=40", { method: "POST" }); setNote("SIMULATOR"); } catch { setNote("UNAVAILABLE"); } await load(); }}>{t("arm")}</button>
        <button className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm" onClick={async () => { try { await api("/api/market/replay/step", { method: "POST" }); } catch { setNote("UNAVAILABLE"); } await load(); }}>{t("step")}</button>
        <button className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm" onClick={async () => { await api("/api/cycle", { method: "POST" }); await load(); }}>{t("runCycle")}</button>
        <button className="rounded-lg bg-[var(--danger)] px-3 py-2 text-sm text-white" onClick={async () => { await api("/api/broker/kill", { method: "POST" }); await load(); }}>{t("kill")}</button>
      </div>
      {note && <p className="mb-3 text-sm text-[var(--gold)]">{note}</p>}
      {book && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Card title={t("bid")} value={book.bid == null ? "—" : book.bid.toFixed(2)} />
          <Card title={t("ask")} value={book.ask == null ? "—" : book.ask.toFixed(2)} />
          <Card title={t("spread")} value={book.spread_points == null ? "—" : String(book.spread_points)} />
          <Card title={t("market")} value={book.index >= 0 ? `${book.state}\n${book.index + 1}/${book.total}` : book.state} />
        </div>
      )}
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
      <div>
        <h2 className="mb-2 text-sm text-[var(--muted)]">{t("positions")}</h2>
        {open.length === 0 ? <p className="text-sm text-[var(--muted)]">{t("empty")}</p> : (
          <div className="space-y-2">
            {open.map((item) => (
              <article key={item.id} className="flex items-center justify-between rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] px-3 py-2 text-sm">
                <span className={item.side === "buy" ? "text-[var(--buy)]" : "text-[var(--sell)]"}>{item.side}</span>
                <span>{item.remaining} @ {item.entry}</span>
              </article>
            ))}
          </div>
        )}
      </div>
      <Notifications />
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
    <section className="mx-auto max-w-3xl space-y-4">
      <VoicePanel />
      <div className="space-y-2">
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
        <input className="min-w-0 flex-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2" value={text} onChange={(event) => setText(event.target.value)} />
        <button className="rounded-lg bg-[var(--gold)] px-3 py-2 text-black" type="submit">{t("send")}</button>
      </form>
    </section>
  );
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
        autoSize: true,
        rightPriceScale: { minimumWidth: 72 },
        localization: { locale: "en-US" },
        layout: { attributionLogo: false, background: { type: ColorType.Solid, color: "#12161d" }, textColor: "#ece8e1" },
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
      <div ref={ref} dir="ltr" className="chart-ltr h-[320px] w-full rounded-[var(--radius)] border border-[var(--line)] md:h-[420px]" />
    </section>
  );
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
export function Lessons() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<{ rule_id: string; summary: string; outcome: string }[]>([]);
  useEffect(() => { void api<{ lessons: { rule_id: string; summary: string; outcome: string }[] }>("/api/lessons").then((body) => setRows(body.lessons)); }, []);
  if (rows.length === 0) return <p className="text-[var(--muted)]">{t("empty")}</p>;
  return (
    <section className="space-y-2">
      {rows.map((row) => (
        <article key={`${row.rule_id}-${row.summary}`} className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4 text-sm">
          <div className="text-[var(--gold)]">{row.rule_id}</div>
          <p className="mt-1">{row.summary}</p>
          <p className="text-xs text-[var(--muted)]">{row.outcome}</p>
        </article>
      ))}
    </section>
  );
}

type ProviderRow = { id: string; provider: string; display_runtime: string; status: string; configured: boolean };

export function Settings() {
  const { t, i18n } = useTranslation();
  const [live, setLive] = useState(false);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [orders, setOrders] = useState("paper");
  const [meta, setMeta] = useState("");
  useEffect(() => {
    void api<{ live_confirmed: boolean; capabilities: string[]; providers: ProviderRow[] }>("/api/settings").then((body) => {
      setLive(body.live_confirmed);
      setCapabilities(body.capabilities);
      setProviders(body.providers);
    });
    void api<{ orders: string; metaapi: string; detail: string }>("/api/live").then((body) => {
      setOrders(body.orders);
      setMeta(`${body.metaapi}: ${body.detail}`);
    });
  }, []);
  return (
    <section className="max-w-3xl space-y-4">
      <div className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4 text-sm">
        <div className="mb-2 text-[var(--muted)]">{t("runtime")}</div>
        <div>{capabilities.join(" · ") || "—"}</div>
        <p className="mt-3 text-[var(--gold)]">{t("ordersPaper")} {orders}</p>
        <p className="mt-1 text-xs text-[var(--muted)]">{meta}</p>
        <p className="mt-2 text-xs text-[var(--muted)]">{t("liveLocked")}</p>
      </div>
      <div className="space-y-2">
        {providers.map((row) => (
          <article key={row.id} className="rounded-lg border border-[var(--line)] bg-[var(--card)] p-3 text-sm">
            <div>{row.provider}</div>
            <div className="text-xs text-[var(--muted)]">{row.display_runtime}</div>
            <div className="text-xs">{row.status}</div>
          </article>
        ))}
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
    </section>
  );
}
