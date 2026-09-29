import { CandlestickSeries, ColorType, createChart, type CandlestickData, type IChartApi, type ISeriesApi, type Time } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./api";
import { InlineChart } from "./chart";
import { RecommendationCard, type Recommendation } from "./desk";
import { applyDirection } from "./i18n";
import { Notifications, useVoiceSession } from "./panels";
import { displayName, setDisplayName } from "./profile";

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

export function Dashboard() {
  const { t } = useTranslation();
  const [data, setData] = useState<Dash | null>(null);
  async function load() {
    setData(await api<Dash>("/api/dashboard"));
  }
  useEffect(() => { void load(); }, []);
  const book = data?.book;
  const open = (data?.broker.positions || []).filter((item) => item.status === "open");
  const priced = book?.bid != null && book?.ask != null;
  const mid = priced && book.bid != null && book.ask != null ? ((book.bid + book.ask) / 2).toFixed(2) : "—";
  const spread = book?.spread_points == null ? "—" : String(book.spread_points);
  let next = t("desk.nextLoad");
  if (data?.broker.killed) next = t("desk.nextKilled");
  else if (open.length > 0) next = t("desk.nextPosition");
  else if (priced) next = t("desk.nextCycle");
  return (
    <section className="mx-auto w-full max-w-3xl space-y-4">
      <header>
        <p className="text-sm text-[var(--muted)]"><span className="latin">XAUUSD</span></p>
        <p className="desk-price latin" dir="ltr">{mid}</p>
      </header>
      <article className="card space-y-2 p-4">
        <p>{t("desk.bidAsk", { bid: book?.bid == null ? "—" : book.bid.toFixed(2), ask: book?.ask == null ? "—" : book.ask.toFixed(2) })}</p>
        <p>{t("desk.spreadLine", { points: spread })}</p>
        {data && <p className="text-sm text-[var(--muted)]">{t("desk.balanceLine", { balance: data.broker.balance.toFixed(2) })}</p>}
      </article>
      <article className="card space-y-2 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("desk.position")}</h2>
        {open.length === 0 ? <p>{t("desk.flat")}</p> : open.map((item) => (
          <p key={item.id}>
            {t("desk.positionLine", {
              side: item.side === "buy" ? t("desk.buy") : t("desk.sell"),
              lots: item.remaining,
              entry: item.entry,
            })}
          </p>
        ))}
      </article>
      <article className="card space-y-2 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("desk.next")}</h2>
        <p>{next}</p>
      </article>
      <div className="flex flex-wrap items-center gap-2">
        <button className="quiet" onClick={async () => { await api("/api/market/replay/synthetic", { method: "POST" }); await load(); }}>{t("loadReplay")}</button>
        <button className="quiet" onClick={async () => { try { await api("/api/market/replay/step", { method: "POST" }); } catch { /* no tape yet */ } await load(); }}>{t("step")}</button>
        <button className="quiet" onClick={async () => { await api("/api/cycle", { method: "POST" }); await load(); }}>{t("runCycle")}</button>
        <button className="quiet danger" onClick={async () => { await api("/api/broker/kill", { method: "POST" }); await load(); }}>{t("kill")}</button>
      </div>
      <Notifications />
    </section>
  );
}

type ChatReply = {
  text: string;
  chart?: { instrument: string };
  recommendation?: Recommendation;
};

export function Chat({ openAttach, includeMarket, includeNews }: { openAttach: () => void; includeMarket: boolean; includeNews: boolean }) {
  const { t, i18n } = useTranslation();
  const [text, setText] = useState("");
  const [lines, setLines] = useState<{ role: string; body: string; chart?: boolean; recommendation?: Recommendation }[]>([]);
  const [name, setName] = useState(displayName());
  const voice = useVoiceSession();
  useEffect(() => {
    const onDraft = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      setText((current) => current ? `${current}\n${detail}` : detail);
    };
    const onNew = () => { setLines([]); setText(""); };
    const onProfile = () => setName(displayName());
    const onVoice = (event: Event) => {
      const detail = (event as CustomEvent<{ transcript: string; reply: string; chart?: { instrument: string }; recommendation?: Recommendation }>).detail;
      if (!detail?.transcript) return;
      setLines((current) => [
        ...current,
        { role: "user", body: detail.transcript },
        { role: "mokli", body: detail.reply, chart: Boolean(detail.chart), recommendation: detail.recommendation },
      ]);
    };
    window.addEventListener("mokli-draft", onDraft);
    window.addEventListener("mokli-new-chat", onNew);
    window.addEventListener("mokli-profile", onProfile);
    window.addEventListener("mokli-voice-line", onVoice);
    return () => {
      window.removeEventListener("mokli-draft", onDraft);
      window.removeEventListener("mokli-new-chat", onNew);
      window.removeEventListener("mokli-profile", onProfile);
      window.removeEventListener("mokli-voice-line", onVoice);
    };
  }, []);
  const day = new Date().getDay();
  const greet = i18n.language === "ar"
    ? ["أحد سعيد", "اثنين سعيد", "ثلاثاء سعيد", "أربعاء سعيد", "خميس سعيد", "جمعة سعيدة", "سبت سعيد"][day]
    : ["Happy Sunday", "Happy Monday", "Happy Tuesday", "Happy Wednesday", "Happy Thursday", "Happy Friday", "Happy Saturday"][day];
  return (
    <section className="chat-stage" data-voice-state={voice.state}>
      <div className="chat-log">
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4">
        {lines.length === 0 ? (
          <div className="greeting">
            <CamelMark />
            <h1>{greet}، <span className="latin">{name}</span></h1>
          </div>
        ) : lines.map((line, index) => (
          <article key={index} className="py-3 text-[17px] leading-7">
            {line.body}
            {line.chart && <InlineChart />}
            {line.recommendation && <RecommendationCard row={line.recommendation} />}
          </article>
        ))}
      </div>
      </div>
      {(voice.state === "listening" || voice.state === "thinking" || voice.state === "speaking") && (
        <p className="px-4 text-center text-sm text-[var(--muted)]">{t(`voiceState.${voice.state}`)}</p>
      )}
      <form className="composer" onSubmit={async (event) => {
        event.preventDefault();
        const message = text.trim();
        if (!message) return;
        setText("");
        setLines((current) => [...current, { role: "user", body: message }]);
        const reply = await api<ChatReply>("/api/chat", {
          method: "POST",
          body: JSON.stringify({ message, include_market: includeMarket, include_news: includeNews }),
        });
        setLines((current) => [...current, {
          role: "mokli",
          body: reply.text,
          chart: Boolean(reply.chart),
          recommendation: reply.recommendation,
        }]);
      }}>
        <button className="plus" type="button" aria-label={t("attachTitle")} onClick={openAttach}>+</button>
        <input dir="auto" placeholder={t("composer")} value={text} onChange={(event) => setText(event.target.value)} />
        <button
          className="mic"
          data-hot={voice.state === "speaking" ? "true" : "false"}
          type="button"
          aria-label={voice.state === "speaking" ? t("barge") : t("talk")}
          onClick={() => { if (voice.state === "speaking") void voice.barge(); else void voice.open(); }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="3" width="6" height="11" rx="3" />
            <path d="M6 11a6 6 0 0 0 12 0M12 17v4" />
          </svg>
        </button>
      </form>
    </section>
  );
}

function CamelMark() {
  return (
    <svg className="camel" viewBox="0 0 96 56" aria-hidden="true">
      <rect x="22" y="40" width="5" height="12" rx="1.5" fill="currentColor" />
      <rect x="32" y="40" width="5" height="12" rx="1.5" fill="currentColor" />
      <rect x="50" y="40" width="5" height="12" rx="1.5" fill="currentColor" />
      <rect x="60" y="40" width="5" height="12" rx="1.5" fill="currentColor" />
      <ellipse cx="42" cy="36" rx="26" ry="10" fill="currentColor" />
      <ellipse cx="50" cy="26" rx="14" ry="9" fill="currentColor" />
      <path d="M64 30c8-2 12-10 10-18" stroke="currentColor" strokeWidth="5" fill="none" strokeLinecap="round" />
      <ellipse cx="78" cy="12" rx="9" ry="5" fill="currentColor" />
      <circle cx="44" cy="14" r="3.2" fill="currentColor" />
      <path d="M44 17v7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Debate() {
  const { t } = useTranslation();
  const [notes, setNotes] = useState<{ role: string; text: string }[]>([]);
  return (
    <section className="mx-auto w-full max-w-3xl">
      <h1 className="screen-title">{t("nav.debate")}</h1>
      <button className="quiet mb-3" onClick={async () => {
        const cycle = await api<{ notes: { role: string; text: string }[] }>("/api/cycle", { method: "POST" });
        setNotes(cycle.notes || []);
      }}>{t("runCycle")}</button>
      {notes.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        {notes.map((note) => (
          <article key={note.role} className="card p-4">
            <h3 className="mb-1 text-[var(--gold)]">{note.role}</h3>
            <p className="text-sm">{note.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

type AxisTick = { label: string; x: number };

function candleStamp(time: Time | number): string {
  const unix = typeof time === "number" ? time : typeof time === "string" ? Math.floor(Date.parse(time) / 1000) : Math.floor(Date.UTC(time.year, time.month - 1, time.day) / 1000);
  const date = new Date(unix * 1000);
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hour = String(date.getUTCHours()).padStart(2, "0");
  const minute = String(date.getUTCMinutes()).padStart(2, "0");
  return `${month}-${day} ${hour}:${minute}`;
}

export function ChartPage() {
  const ref = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  const [ticks, setTicks] = useState<AxisTick[]>([]);
  useEffect(() => {
    if (!ref.current) return;
    let chart: IChartApi | null = null;
    let series: ISeriesApi<"Candlestick"> | null = null;
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
        if (previous && x - previous.x < 96) {
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
      series = chart.addSeries(CandlestickSeries, { upColor: "#2fbf8a", downColor: "#e15d66", borderVisible: false, wickUpColor: "#2fbf8a", wickDownColor: "#e15d66" });
      const rows: CandlestickData[] = payload.candles.map((candle) => ({
        time: Math.floor(new Date(candle.time).getTime() / 1000) as CandlestickData["time"],
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }));
      if (!series || !chart) return;
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
    <section className="mx-auto w-full max-w-4xl">
      <h1 className="screen-title">{t("nav.charts")}</h1>
      <div ref={ref} dir="ltr" className="chart-ltr h-[320px] w-full rounded-[var(--radius)] border border-[var(--line)] md:h-[420px]" />
      <div dir="ltr" data-chart-axis className="chart-axis">
        {ticks.map((tick) => (
          <span key={tick.label} style={{ left: tick.x, transform: tick.x < 56 ? "none" : "translateX(-50%)" }}>{tick.label}</span>
        ))}
      </div>
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
    <section className="mx-auto w-full max-w-3xl space-y-3">
      <h1 className="screen-title">{t("nav.approvals")}</h1>
      {rows.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
      {rows.map((row) => (
        <article key={row.id} className="card p-4">
          <p><span className="latin">{row.payload.side}</span> @ <span className="latin">{row.payload.entry}</span></p>
          <div className="mt-2 flex gap-2">
            <button className="quiet" style={{ color: "var(--buy)" }} onClick={async () => { await api(`/api/approvals/${row.id}/approve`, { method: "POST" }); await load(); }}>{t("approve")}</button>
            <button className="quiet" style={{ color: "var(--sell)" }} onClick={async () => { await api(`/api/approvals/${row.id}/reject`, { method: "POST" }); await load(); }}>{t("reject")}</button>
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
  const [name, setName] = useState(displayName());
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
    <section className="mx-auto w-full max-w-lg space-y-4">
      <h1 className="screen-title">{t("nav.settings")}</h1>
      <div className="avatar">{name.slice(0, 1).toUpperCase()}</div>
      <label className="block text-sm text-[var(--muted)]">{t("name")}</label>
      <input className="field latin" value={name} onChange={(event) => setName(event.target.value)} />
      <button className="quiet w-full" type="button" onClick={() => setDisplayName(name)}>{t("saveProfile")}</button>
      <div className="card p-4 text-sm">
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
      <select className="field" value={i18n.language} onChange={async (event) => {
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
