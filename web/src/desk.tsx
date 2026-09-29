import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./api";
import { applyDirection } from "./i18n";
import { displayName, setDisplayName } from "./profile";

export type Recommendation = {
  id: string;
  direction: string;
  entry: number | null;
  stop: number | null;
  targets: number[];
  size?: number | null;
  rationale: string;
  confidence: string | null;
  outcome: string;
};

type Connection = { id: string; name: string; group: string; connected: boolean };

export type BotCardData = {
  id: string;
  name: string;
  kind: string;
  instrument: string;
  timeframe: string;
  entry: string;
  exit: string;
  stop: string;
  size_rule: string;
  session: string;
  status: string;
};

type SettingsBody = {
  language: string;
  active_provider: string;
  mode: string;
  orders: string;
  mokli_host: string;
  live_orders: boolean;
  broker_connected: boolean;
  live_locked: boolean;
  risk: {
    risk_fraction: number;
    daily_loss_fraction: number;
    min_reward_risk: number;
    cooldown_minutes: number;
    max_open_positions: number;
  };
  connections: Connection[];
};

type Performance = {
  equity_r: number;
  win_rate: number | null;
  expectancy_r: number | null;
  open_position: { side: string; lots: number; entry: number; stop: number | null } | null;
  daily_loss: number;
  daily_limit: number;
};

function directionLabel(direction: string, t: (key: string) => string) {
  if (direction === "buy") return t("desk.buy");
  if (direction === "sell") return t("desk.sell");
  return t("rec.wait");
}

export function RecommendationCard({ row }: { row: Recommendation }) {
  const { t } = useTranslation();
  const tone = row.direction === "buy" ? "text-[var(--buy)]" : row.direction === "sell" ? "text-[var(--sell)]" : "text-[var(--muted)]";
  return (
    <article data-recommendation className="card mt-3 space-y-2 p-4">
      <div className="flex items-center justify-between">
        <span className="latin text-sm text-[var(--muted)]">XAUUSD</span>
        <span className={tone}>{directionLabel(row.direction, t)}</span>
      </div>
      <p><span className="text-[var(--muted)]">{t("rec.entry")}</span> <span className="latin">{row.entry ?? "—"}</span></p>
      <p><span className="text-[var(--muted)]">{t("rec.stop")}</span> <span className="latin">{row.stop ?? "—"}</span></p>
      <p><span className="text-[var(--muted)]">{t("rec.targets")}</span> <span className="latin">{row.targets.length ? row.targets.join(" · ") : "—"}</span></p>
      {row.size != null && <p><span className="text-[var(--muted)]">{t("rec.size")}</span> <span className="latin">{row.size}</span></p>}
      <p>{row.rationale}</p>
      <p className="text-sm text-[var(--muted)]">{t("rec.confidence")} <span className="latin">{row.confidence ?? "—"}</span></p>
      {row.direction === "buy" || row.direction === "sell" ? <p>{t("rec.ask")}</p> : null}
      <p className="text-sm text-[var(--muted)]">{t("rec.outcome")} {t(`rec.outcomes.${row.outcome}`, { defaultValue: row.outcome })}</p>
    </article>
  );
}

export function BotCard({ bot }: { bot: BotCardData }) {
  const { t } = useTranslation();
  return (
    <article data-bot={bot.id} className="card mt-3 space-y-2 p-4">
      <div className="flex items-center justify-between gap-3">
        <span>{bot.name}</span>
        <span className="latin text-sm text-[var(--muted)]">{bot.instrument}</span>
      </div>
      <p><span className="text-[var(--muted)]">{t("bot.kind")}</span> <span className="latin">{bot.kind}</span></p>
      <p><span className="text-[var(--muted)]">{t("bot.timeframe")}</span> <span className="latin">{bot.timeframe}</span></p>
      <p><span className="text-[var(--muted)]">{t("bot.entry")}</span> {bot.entry}</p>
      <p><span className="text-[var(--muted)]">{t("bot.exit")}</span> {bot.exit}</p>
      <p><span className="text-[var(--muted)]">{t("bot.stop")}</span> {bot.stop}</p>
      <p><span className="text-[var(--muted)]">{t("bot.size")}</span> <span className="latin">{bot.size_rule}</span></p>
      <p><span className="text-[var(--muted)]">{t("bot.session")}</span> <span className="latin">{bot.session}</span></p>
      <p className="text-sm text-[var(--muted)]">{bot.status === "paused" ? t("bot.paused") : t("bot.active")}</p>
    </article>
  );
}

export function Recommendations() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Recommendation[]>([]);
  useEffect(() => {
    void api<{ recommendations: Recommendation[] }>("/api/recommendations").then((body) => setRows(body.recommendations));
  }, []);
  return (
    <section className="mx-auto w-full max-w-2xl space-y-3">
      <h1 className="screen-title">{t("nav.recommendations")}</h1>
      {rows.length === 0 ? <p className="text-[var(--muted)]">{t("empty")}</p> : rows.map((row) => (
        <RecommendationCard key={row.id || row.rationale} row={row} />
      ))}
    </section>
  );
}

export function Performance() {
  const { t } = useTranslation();
  const [view, setView] = useState<Performance | null>(null);
  useEffect(() => {
    void api<Performance>("/api/performance").then(setView);
  }, []);
  if (!view) return <p className="text-[var(--muted)]">{t("empty")}</p>;
  const open = view.open_position;
  return (
    <section className="mx-auto w-full max-w-2xl space-y-4">
      <h1 className="screen-title">{t("nav.performance")}</h1>
      <p className="text-sm text-[var(--muted)]">{t("perf.equity")}</p>
      <p className="perf-figure latin" dir="ltr">{view.equity_r.toFixed(2)} R</p>
      <article className="card space-y-2 p-4">
        <p>{t("perf.win")} <span className="latin">{view.win_rate == null ? "—" : `${Math.round(view.win_rate * 100)}%`}</span></p>
        <p>{t("perf.expectancy")} <span className="latin">{view.expectancy_r == null ? "—" : `${view.expectancy_r.toFixed(2)} R`}</span></p>
        <p>{t("perf.daily")} <span className="latin">{(view.daily_loss * 100).toFixed(2)}% / {(view.daily_limit * 100).toFixed(0)}%</span></p>
      </article>
      <article className="card space-y-2 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("desk.position")}</h2>
        {open ? (
          <p>{t("desk.positionLine", { side: open.side === "buy" ? t("desk.buy") : t("desk.sell"), lots: open.lots, entry: open.entry })}</p>
        ) : <p>{t("desk.flat")}</p>}
      </article>
    </section>
  );
}

export function Settings() {
  const { t, i18n } = useTranslation();
  const [body, setBody] = useState<SettingsBody | null>(null);
  const [name, setName] = useState(displayName());
  const [host, setHost] = useState("");
  const [risk, setRisk] = useState({ risk_fraction: "", daily_loss_fraction: "", min_reward_risk: "", cooldown_minutes: "", max_open_positions: "" });
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [accounts, setAccounts] = useState<Record<string, string>>({});
  const [bots, setBots] = useState<BotCardData[]>([]);
  const [note, setNote] = useState("");
  async function load() {
    const next = await api<SettingsBody>("/api/settings");
    setBody(next);
    setHost(next.mokli_host);
    setRisk({
      risk_fraction: String(next.risk.risk_fraction),
      daily_loss_fraction: String(next.risk.daily_loss_fraction),
      min_reward_risk: String(next.risk.min_reward_risk),
      cooldown_minutes: String(next.risk.cooldown_minutes),
      max_open_positions: String(next.risk.max_open_positions),
    });
    const listed = await api<{ bots: BotCardData[] }>("/api/bots");
    setBots(listed.bots);
  }
  useEffect(() => { void load(); }, []);
  if (!body) return <p className="text-[var(--muted)]">{t("empty")}</p>;
  const models = body.connections.filter((item) => item.group === "model");
  const markets = body.connections.filter((item) => item.group === "market");
  return (
    <section className="mx-auto w-full max-w-lg space-y-6">
      <h1 className="screen-title">{t("nav.settings")}</h1>
      <article className="card space-y-3 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("settings.env")}</h2>
        <p>{t("settings.paperLocked")}</p>
        <label className="block text-sm text-[var(--muted)]">{t("settings.bind")}</label>
        <input className="field latin" dir="ltr" value={host} onChange={(event) => setHost(event.target.value)} />
        <button className="quiet" type="button" onClick={async () => {
          const next = await api<SettingsBody>("/api/settings", { method: "PUT", body: JSON.stringify({ mokli_host: host }) });
          setBody(next);
          setNote(t("settings.saved"));
        }}>{t("settings.save")}</button>
        {(["risk_fraction", "daily_loss_fraction", "min_reward_risk", "cooldown_minutes", "max_open_positions"] as const).map((key) => (
          <label key={key} className="block text-sm">
            <span className="text-[var(--muted)]">{t(`settings.${key}`)}</span>
            <input className="field latin mt-1" dir="ltr" value={risk[key]} onChange={(event) => setRisk({ ...risk, [key]: event.target.value })} />
          </label>
        ))}
        <button className="quiet" type="button" onClick={async () => {
          try {
            const next = await api<SettingsBody>("/api/settings", {
              method: "PUT",
              body: JSON.stringify({
                risk_fraction: Number(risk.risk_fraction),
                daily_loss_fraction: Number(risk.daily_loss_fraction),
                min_reward_risk: Number(risk.min_reward_risk),
                cooldown_minutes: Number(risk.cooldown_minutes),
                max_open_positions: Number(risk.max_open_positions),
              }),
            });
            setBody(next);
            setNote(t("settings.saved"));
          } catch {
            setNote(t("settings.refused"));
          }
        }}>{t("settings.saveRisk")}</button>
      </article>
      <article className="card space-y-3 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("settings.model")}</h2>
        <label className="block text-sm text-[var(--muted)]">{t("settings.active")}</label>
        <select className="field" value={body.active_provider} onChange={async (event) => {
          const next = await api<SettingsBody>("/api/settings", { method: "PUT", body: JSON.stringify({ active_provider: event.target.value }) });
          setBody(next);
        }}>
          <option value="mokli">Mokli</option>
          {models.filter((item) => item.connected).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        {models.map((item) => (
          <ProviderRow key={item.id} row={item} secret={secrets[item.id] || ""} account={accounts[item.id] || ""} onSecret={(value) => setSecrets({ ...secrets, [item.id]: value })} onAccount={(value) => setAccounts({ ...accounts, [item.id]: value })} onDone={async (next) => { setBody(next); setSecrets({ ...secrets, [item.id]: "" }); setAccounts({ ...accounts, [item.id]: "" }); }} />
        ))}
      </article>
      <article className="card space-y-3 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("settings.market")}</h2>
        {markets.map((item) => (
          <ProviderRow key={item.id} row={item} secret={secrets[item.id] || ""} account={accounts[item.id] || ""} onSecret={(value) => setSecrets({ ...secrets, [item.id]: value })} onAccount={(value) => setAccounts({ ...accounts, [item.id]: value })} onDone={async (next) => { setBody(next); setSecrets({ ...secrets, [item.id]: "" }); setAccounts({ ...accounts, [item.id]: "" }); }} />
        ))}
      </article>
      <article className="card space-y-2 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("name")}</h2>
        <input className="field latin" value={name} onChange={(event) => setName(event.target.value)} />
        <button className="quiet" type="button" onClick={() => setDisplayName(name)}>{t("saveProfile")}</button>
        <label className="block text-sm text-[var(--muted)]">{t("language")}</label>
        <select className="field" value={i18n.language} onChange={async (event) => {
          const language = event.target.value;
          await i18n.changeLanguage(language);
          applyDirection(language);
          await api("/api/settings", { method: "PUT", body: JSON.stringify({ language }) });
        }}>
          <option value="ar">العربية</option>
          <option value="en">English</option>
        </select>
      </article>
      <article className="card space-y-3 p-4">
        <h2 className="text-sm text-[var(--muted)]">{t("settings.bots")}</h2>
        {bots.length === 0 ? <p className="text-sm text-[var(--muted)]">{t("empty")}</p> : bots.map((bot) => (
          <div key={bot.id} className="space-y-2" data-saved-bot={bot.id}>
            <BotCard bot={bot} />
            <div className="flex gap-2">
              <button className="quiet" type="button" onClick={async () => {
                const path = bot.status === "paused" ? "resume" : "pause";
                await api(`/api/bots/${bot.id}/${path}`, { method: "POST" });
                await load();
              }}>{bot.status === "paused" ? t("bot.resume") : t("bot.pause")}</button>
              <button className="quiet" type="button" onClick={async () => {
                await api(`/api/bots/${bot.id}`, { method: "DELETE" });
                await load();
              }}>{t("bot.delete")}</button>
            </div>
          </div>
        ))}
      </article>
      <article className="card space-y-3 p-4" data-live-lock>
        <p>{body.live_orders ? t("settings.liveOn") : t("settings.liveOff")}</p>
        <button className="toggle" type="button" data-live-switch disabled={!body.broker_connected} onClick={async () => {
          const next = await api<SettingsBody>("/api/settings", { method: "PUT", body: JSON.stringify({ live_orders: !body.live_orders }) });
          setBody(next);
        }}>
          <span>{t("settings.liveSwitch")}</span>
          <span className="switch" data-on={body.live_orders ? "true" : "false"}><i /></span>
        </button>
        {!body.broker_connected && <p className="text-sm text-[var(--muted)]">{t("settings.liveNeedsBroker")}</p>}
        <p className="text-sm text-[var(--muted)]"><span className="latin">{body.mode}</span> · <span className="latin">{body.orders}</span></p>
      </article>
      {note && <p className="text-sm text-[var(--muted)]">{note}</p>}
    </section>
  );
}

function ProviderRow({ row, secret, account, onSecret, onAccount, onDone }: { row: Connection; secret: string; account: string; onSecret: (value: string) => void; onAccount: (value: string) => void; onDone: (body: SettingsBody) => void }) {
  const { t } = useTranslation();
  const needsAccount = row.id === "oanda" || row.id === "metaapi";
  return (
    <div className="rounded-2xl border border-[var(--line)] p-3" data-provider={row.id}>
      <div className="flex items-center justify-between gap-3">
        <span className="latin">{row.name}</span>
        <span className="text-sm text-[var(--muted)]">{row.connected ? t("settings.connected") : t("settings.disconnected")}</span>
      </div>
      <input className="field mt-2" type="password" autoComplete="new-password" value={secret} placeholder={row.id === "ollama" ? t("settings.modelName") : t("settings.secret")} onChange={(event) => onSecret(event.target.value)} />
      {needsAccount && <input className="field latin mt-2" dir="ltr" autoComplete="off" value={account} placeholder={t("settings.account")} onChange={(event) => onAccount(event.target.value)} />}
      <div className="mt-2 flex gap-2">
        <button className="quiet" type="button" onClick={async () => {
          const payload = row.id === "ollama" ? { id: row.id, account: secret } : { id: row.id, secret, account };
          const next = await api<SettingsBody>("/api/settings/providers", { method: "POST", body: JSON.stringify(payload) });
          onDone(next);
        }}>{t("settings.connect")}</button>
        <button className="quiet" type="button" onClick={async () => {
          const next = await api<SettingsBody>("/api/settings/providers", { method: "POST", body: JSON.stringify({ id: row.id, disconnect: true }) });
          onDone(next);
        }}>{t("settings.disconnect")}</button>
      </div>
    </div>
  );
}
