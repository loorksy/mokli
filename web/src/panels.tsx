import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./api";

type VoiceSnap = {
  state: string;
  transcript: string;
  reply: string;
  provider: string;
  model: string;
  runtime: string;
  agent: string;
  status: string;
  tools: string[];
  interrupted: boolean;
  audio_base64?: string;
  error?: string;
  chart?: { instrument: string };
  recommendation?: {
    id: string;
    direction: string;
    entry: number | null;
    stop: number | null;
    targets: number[];
    rationale: string;
    confidence: string | null;
    outcome: string;
  };
};

type VoicePhase = "idle" | "listening" | "thinking" | "speaking";

async function blobBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = "";
  const step = 0x8000;
  for (let index = 0; index < bytes.length; index += step) {
    binary += String.fromCharCode(...bytes.subarray(index, index + step));
  }
  return btoa(binary);
}

export function useVoiceSession() {
  const { i18n } = useTranslation();
  const [snap, setSnap] = useState<VoiceSnap | null>(null);
  const [phase, setPhase] = useState<VoicePhase>("idle");
  const alive = useRef(true);
  const generation = useRef(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stream = useRef<MediaStream | null>(null);
  const audioCtx = useRef<AudioContext | null>(null);
  const playing = useRef<AudioBufferSourceNode | null>(null);

  useEffect(() => {
    alive.current = true;
    const host = window as unknown as { __mokliSubmitClip?: (audioBase64: string) => Promise<void> };
    host.__mokliSubmitClip = (audioBase64: string) => runClip(audioBase64);
    return () => {
      alive.current = false;
      generation.current += 1;
      recorder.current?.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
      playing.current?.stop();
      void audioCtx.current?.close();
      delete host.__mokliSubmitClip;
    };
  }, []);

  function context(): AudioContext {
    if (!audioCtx.current) {
      audioCtx.current = new AudioContext();
    }
    return audioCtx.current;
  }

  async function playReply(audioBase64: string, gen: number): Promise<void> {
    const ctx = context();
    await ctx.resume();
    const raw = Uint8Array.from(atob(audioBase64), (char) => char.charCodeAt(0));
    const buffer = await ctx.decodeAudioData(raw.buffer.slice(0));
    if (!alive.current || generation.current !== gen) return;
    await new Promise<void>((resolve) => {
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      playing.current = source;
      source.onended = () => {
        if (playing.current === source) playing.current = null;
        resolve();
      };
      source.start();
    });
  }

  async function finishTurn(gen: number) {
    if (!alive.current || generation.current !== gen) return;
    const next = await api<VoiceSnap>("/api/voice/spoken", { method: "POST" });
    if (!alive.current || generation.current !== gen) return;
    setSnap(next);
    setPhase("idle");
  }

  async function runClip(audioBase64: string) {
    const gen = generation.current;
    setPhase("thinking");
    const spoken = await api<VoiceSnap>("/api/voice/turn", {
      method: "POST",
      body: JSON.stringify({ audio_base64: audioBase64, lang: i18n.language === "ar" ? "ar" : "en" }),
    });
    if (!alive.current || generation.current !== gen) return;
    setSnap(spoken);
    if (spoken.error || spoken.state !== "speaking" || !spoken.audio_base64) {
      setPhase("idle");
      return;
    }
    setPhase("speaking");
    window.dispatchEvent(new CustomEvent("mokli-voice-line", {
      detail: {
        transcript: spoken.transcript,
        reply: spoken.reply,
        chart: spoken.chart,
        recommendation: spoken.recommendation,
      },
    }));
    try {
      await playReply(spoken.audio_base64, gen);
    } catch {
      /* A missing decoder still ends the turn. The reply audio was produced. */
    }
    await finishTurn(gen);
  }

  function stopRecorder() {
    const active = recorder.current;
    if (active && active.state === "recording") active.stop();
  }

  async function beginRecording() {
    const gen = generation.current;
    const started = await api<VoiceSnap>("/api/voice/start", { method: "POST" });
    if (!alive.current || generation.current !== gen) return;
    setSnap(started);
    setPhase("listening");
    let media: MediaStream;
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      await api("/api/voice/stop", { method: "POST" });
      if (alive.current && generation.current === gen) setPhase("idle");
      return;
    }
    if (!alive.current || generation.current !== gen) {
      media.getTracks().forEach((track) => track.stop());
      return;
    }
    stream.current = media;
    const rec = new MediaRecorder(media);
    chunks.current = [];
    rec.ondataavailable = (event) => {
      if (event.data.size) chunks.current.push(event.data);
    };
    rec.onstop = () => {
      media.getTracks().forEach((track) => track.stop());
      const blob = new Blob(chunks.current, { type: rec.mimeType || "audio/webm" });
      if (!alive.current || generation.current !== gen || blob.size === 0) {
        if (blob.size === 0) void api("/api/voice/stop", { method: "POST" });
        if (alive.current) setPhase("idle");
        return;
      }
      void blobBase64(blob).then((encoded) => runClip(encoded));
    };
    recorder.current = rec;
    rec.start();
    window.setTimeout(() => {
      if (generation.current === gen) stopRecorder();
    }, 1600);
  }

  async function open() {
    await context().resume();
    if (phase === "listening") {
      stopRecorder();
      return;
    }
    if (phase === "speaking") {
      await barge();
      return;
    }
    await beginRecording();
  }

  async function barge() {
    generation.current += 1;
    playing.current?.stop();
    recorder.current?.stop();
    const next = await api<VoiceSnap>("/api/voice/barge", { method: "POST" });
    if (!alive.current) return;
    setSnap(next);
    await beginRecording();
  }

  return { snap, state: phase, open, barge };
}

export function Activity() {
  const { t } = useTranslation();
  const [body, setBody] = useState<{ events: { kind: string; at: string }[]; providers: { provider: string; runtime: string; model: string; fallback_provider: string; fallback_reason: string }[] } | null>(null);
  useEffect(() => { void api<typeof body>("/api/activity").then(setBody); }, []);
  if (!body) return <p className="text-[var(--muted)]">{t("empty")}</p>;
  const fallback = body.providers.find((item) => item.fallback_provider);
  return (
    <section className="space-y-3">
      {fallback && (
        <div className="rounded-[var(--radius)] border border-[var(--gold)] bg-[var(--card)] p-4 text-sm">
          {t("fallback")} {fallback.provider} → {fallback.fallback_provider}: {fallback.fallback_reason}
        </div>
      )}
      <div className="space-y-2">
        {body.events.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
        {body.events.map((event, index) => (
          <div key={`${event.at}-${index}`} className="flex items-center justify-between gap-3 rounded-lg border border-[var(--line)] bg-[var(--card)] px-3 py-2 text-sm">
            <span>{event.kind}</span>
            <span className="text-xs text-[var(--muted)]">{event.at.slice(11, 19)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

type Node = { id: string; parent_id: string | null; role: string; provider: string; runtime: string; model: string; status: string };

export function Agents() {
  const { t } = useTranslation();
  const [nodes, setNodes] = useState<Node[]>([]);
  useEffect(() => { void api<{ nodes: Node[] }>("/api/agents/tree").then((body) => setNodes(body.nodes)); }, []);
  const roots = nodes.filter((node) => !node.parent_id);
  const withChildren = roots.filter((root) => nodes.some((node) => node.parent_id === root.id));
  const shown = (withChildren.length > 0 ? withChildren : roots).slice(0, 3);
  if (nodes.length === 0) return <p className="text-[var(--muted)]">{t("empty")}</p>;
  return (
    <section className="space-y-3">
      {shown.map((root) => (
        <article key={root.id} className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4">
          <header className="mb-2">
            <div className="text-[var(--gold)]">{root.role}</div>
            <div className="text-xs text-[var(--muted)]">{root.provider} · {root.model} · {root.runtime} · {root.status}</div>
          </header>
          <div className="grid gap-2 md:grid-cols-2">
            {nodes.filter((node) => node.parent_id === root.id).map((child) => (
              <div key={child.id} className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm">
                <div>{child.role}</div>
                <div className="text-xs text-[var(--muted)]">{child.provider} · {child.runtime} · {child.status}</div>
              </div>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

export function News() {
  const { t } = useTranslation();
  const [body, setBody] = useState<{ phase: string; detail: string; calendar: string; candle_rules: string[] } | null>(null);
  useEffect(() => { void api<typeof body>("/api/news").then(setBody); }, []);
  if (!body) return <p className="text-[var(--muted)]">{t("empty")}</p>;
  return (
    <section className="space-y-3">
      <div className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4">
        <div className="text-xs text-[var(--muted)]">{t("newsPhase")}</div>
        <div className="text-2xl">{body.phase}</div>
        <p className="mt-2 text-sm">{body.detail}</p>
        <p className="mt-1 text-xs text-[var(--muted)]">{t("calendar")}: {body.calendar}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {body.candle_rules.map((rule) => <span key={rule} className="rounded-full border border-[var(--line)] px-3 py-1 text-xs">{rule}</span>)}
      </div>
    </section>
  );
}

export function Journal() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<{ verdict?: string; decision_id?: string }[]>([]);
  const [memories, setMemories] = useState<{ id: number; kind: string; body: string }[]>([]);
  const [note, setNote] = useState("");
  async function load() {
    const journal = await api<{ entries: { verdict?: string; decision_id?: string }[] }>("/api/journal");
    const memory = await api<{ memories: { id: number; kind: string; body: string }[] }>("/api/memory");
    setEntries(journal.entries);
    setMemories(memory.memories);
  }
  useEffect(() => { void load(); }, []);
  return (
    <section className="mx-auto grid w-full max-w-3xl gap-4 lg:grid-cols-2">
      <div className="space-y-2">
        <h1 className="screen-title">{t("nav.journal")}</h1>
        {entries.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
        {entries.map((entry, index) => (
          <article key={entry.decision_id || index} className="card p-3 text-sm">
            {entry.verdict || t("empty")}
          </article>
        ))}
      </div>
      <div className="space-y-2">
        <h2 className="text-sm text-[var(--muted)]">{t("memory")}</h2>
        <form className="flex gap-2" onSubmit={async (event) => {
          event.preventDefault();
          await api("/api/memory", { method: "POST", body: JSON.stringify({ kind: "note", body: note, tags: note }) });
          setNote("");
          await load();
        }}>
          <input className="field" value={note} onChange={(event) => setNote(event.target.value)} />
          <button className="quiet" type="submit">{t("send")}</button>
        </form>
        {memories.map((item) => (
          <article key={item.id} className="rounded-lg border border-[var(--line)] bg-[var(--card)] p-3 text-sm">{item.body}</article>
        ))}
      </div>
    </section>
  );
}

export function Reports() {
  const { t } = useTranslation();
  const [daily, setDaily] = useState<Record<string, string | number | null> | null>(null);
  const [weekly, setWeekly] = useState<Record<string, string | number | null> | null>(null);
  useEffect(() => {
    void api<Record<string, string | number | null>>("/api/reports/daily").then(setDaily);
    void api<Record<string, string | number | null>>("/api/reports/weekly").then(setWeekly);
  }, []);
  return (
    <section className="grid gap-3 md:grid-cols-2">
      {[daily, weekly].map((report) => report && (
        <article key={String(report.period)} className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4">
          <div className="text-xs text-[var(--muted)]">{String(report.period)}</div>
          <div className="mt-2 text-2xl">{report.balance}</div>
          <p className="text-sm text-[var(--muted)]">{t("equity")} {report.equity}</p>
          <p className="text-sm">{t("closed")} {report.closed_trades} · {t("mode")} {String(report.mode)}</p>
        </article>
      ))}
    </section>
  );
}

type Note = { id: string; level: string; title: string; body: string; read: boolean };

export function Notifications() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Note[]>([]);
  async function load() {
    const body = await api<{ notifications: Note[] }>("/api/notifications");
    setRows(body.notifications);
  }
  useEffect(() => { void load(); }, []);
  if (rows.length === 0) return <p className="text-sm text-[var(--muted)]">{t("empty")}</p>;
  return (
    <section className="space-y-2">
      <h2 className="text-sm text-[var(--muted)]">{t("notifications")}</h2>
      {rows.map((row) => (
        <article key={row.id} className="rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className={row.level === "critical" ? "text-[var(--danger)]" : "text-[var(--gold)]"}>{row.title}</span>
            {!row.read && (
              <button className="text-xs text-[var(--muted)]" onClick={async () => { await api(`/api/notifications/${row.id}/read`, { method: "POST" }); await load(); }} type="button">{t("markRead")}</button>
            )}
          </div>
          <p className="mt-1 text-[var(--muted)]">{row.body}</p>
        </article>
      ))}
    </section>
  );
}

export function Signals() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<{ verdict?: string; blocking_rule?: string | null }[]>([]);
  useEffect(() => { void api<{ entries: { verdict?: string; blocking_rule?: string | null }[] }>("/api/journal").then((body) => setEntries(body.entries)); }, []);
  return (
    <section className="mx-auto w-full max-w-3xl space-y-2">
      <h1 className="screen-title">{t("nav.signals")}</h1>
      {entries.length === 0 && <p className="text-[var(--muted)]">{t("empty")}</p>}
      {entries.map((entry, index) => (
        <article key={index} className="flex items-center justify-between rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-4">
          <span className={entry.verdict === "buy" ? "text-[var(--buy)]" : entry.verdict === "sell" ? "text-[var(--sell)]" : ""}>{entry.verdict}</span>
          <span className="text-xs text-[var(--muted)]">{entry.blocking_rule || "—"}</span>
        </article>
      ))}
    </section>
  );
}
