import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, clearToken, setToken, token } from "./api";
import { Performance, Recommendations, Settings } from "./desk";
import { applyDirection } from "./i18n";
import { flag, setFlag, displayName } from "./profile";
import { Chat } from "./screens";

const nav = [
  ["/", "nav.agent", "agent"],
  ["/recommendations", "nav.recommendations", "recommendations"],
  ["/performance", "nav.performance", "performance"],
] as const;

export default function App() {
  const { t, i18n } = useTranslation();
  const [authed, setAuthed] = useState(Boolean(token()));
  const navigate = useNavigate();
  const location = useLocation();
  const [drawer, setDrawer] = useState(false);
  const [sheet, setSheet] = useState<"account" | "attach" | null>(null);
  const [name, setName] = useState(displayName());
  const [includeMarket, setIncludeMarket] = useState(flag("mokli-market", true));
  const [includeNews, setIncludeNews] = useState(flag("mokli-news", true));
  const chat = location.pathname === "/" || location.pathname === "/chat";

  useEffect(() => {
    applyDirection(i18n.language);
  }, [i18n.language]);

  useEffect(() => {
    const refresh = () => setName(displayName());
    window.addEventListener("mokli-profile", refresh);
    return () => window.removeEventListener("mokli-profile", refresh);
  }, []);

  if (!authed) {
    return <Login onSuccess={() => { setAuthed(true); navigate("/"); }} />;
  }

  function go(path: string) {
    setDrawer(false);
    setSheet(null);
    navigate(path);
  }

  return (
    <div className="shell">
      <aside className="drawer" data-open={drawer ? "true" : "false"}>
        <div className="mb-5 flex items-center justify-between">
          <div className="text-2xl font-medium">{t("app")}</div>
          <span className="pill">{t("paper")}</span>
        </div>
        <button className="side-link" type="button" onClick={() => { window.dispatchEvent(new Event("mokli-new-chat")); go("/"); }}>
          <span aria-hidden="true">+</span>
          <span>{t("newChat")}</span>
        </button>
        <nav className="mt-3 flex-1 overflow-auto" data-nav-list>
          {nav.map(([path, key, id]) => (
            <NavLink key={path} to={path} end={path === "/"} className="side-link" data-nav={id} data-active={location.pathname === path ? "true" : "false"} onClick={() => setDrawer(false)}>
              <span>{t(key)}</span>
            </NavLink>
          ))}
        </nav>
        <button className="side-link" type="button" onClick={() => setSheet("account")}>
          <span className="flex items-center gap-3">
            <span className="avatar small">{name.slice(0, 1).toUpperCase()}</span>
            <span>
              <span className="latin">{name}</span>
              <span className="block text-xs text-[var(--muted)]">{t("paper")}</span>
            </span>
          </span>
        </button>
      </aside>
      {drawer && <button className="backdrop drawer-backdrop" type="button" aria-label={t("close")} onClick={() => setDrawer(false)} />}
      <div className="column">
        <header className="topbar">
          <button className="icon-btn menu-btn" type="button" aria-label={t("menu")} onClick={() => setDrawer(true)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M5 7h14M5 12h14M5 17h10" /></svg>
          </button>
          <button className="pill" type="button" onClick={() => setSheet("account")}>{t("paper")}</button>
          <button className="icon-btn" type="button" aria-label={t("account")} onClick={() => setSheet("account")}>
            <span className="avatar small">{name.slice(0, 1).toUpperCase()}</span>
          </button>
        </header>
        <main className={chat ? "stage" : "stage stage-pad"}>
          <Routes>
            <Route path="/" element={<Chat openAttach={() => setSheet("attach")} includeMarket={includeMarket} includeNews={includeNews} />} />
            <Route path="/chat" element={<Navigate to="/" replace />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
      {sheet === "account" && (
        <Sheet title={t("account")} onClose={() => setSheet(null)}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-lg"><span className="latin">{name}</span></div>
              <div className="text-sm text-[var(--muted)]">{t("paper")}</div>
            </div>
            <span className="avatar small">{name.slice(0, 1).toUpperCase()}</span>
          </div>
          <button className="sheet-row" type="button" data-open-settings onClick={() => go("/settings")}><span>{t("nav.settings")}</span></button>
          <label className="sheet-row">
            <span>{t("language")}</span>
            <select className="field" style={{ width: "auto" }} value={i18n.language} onChange={async (event) => {
              const language = event.target.value;
              await i18n.changeLanguage(language);
              applyDirection(language);
              await api("/api/settings", { method: "PUT", body: JSON.stringify({ language }) });
            }}>
              <option value="ar">العربية</option>
              <option value="en">English</option>
            </select>
          </label>
          <button className="sheet-row" type="button" onClick={() => { clearToken(); setAuthed(false); }}><span>{t("logout")}</span></button>
        </Sheet>
      )}
      {sheet === "attach" && (
        <Sheet title={t("attachTitle")} onClose={() => setSheet(null)}>
          <div className="tiles">
            <FileTile label={t("files")} accept="*/*" onFile={(file) => attachFile(file)} />
            <FileTile label={t("photos")} accept="image/*" onFile={(file) => attachFile(file)} />
            <FileTile label={t("camera")} accept="image/*" capture onFile={(file) => attachFile(file)} />
          </div>
          <Toggle label={t("priceContext")} on={includeMarket} onChange={(on) => { setIncludeMarket(on); setFlag("mokli-market", on); }} />
          <Toggle label={t("newsContext")} on={includeNews} onChange={(on) => { setIncludeNews(on); setFlag("mokli-news", on); }} />
          <p className="mt-2 text-xs text-[var(--muted)]">{t("attachNote")}</p>
        </Sheet>
      )}
    </div>
  );
}

function attachFile(file: File) {
  const line = `${file.type.startsWith("image/") ? "image" : "file"}: ${file.name}`;
  window.dispatchEvent(new CustomEvent("mokli-draft", { detail: line }));
}

function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <>
      <button className="backdrop" type="button" aria-label={title} onClick={onClose} />
      <section className="sheet" role="dialog" aria-label={title}>
        <div className="grabber" />
        <h2>{title}</h2>
        {children}
      </section>
    </>
  );
}

function Toggle({ label, on, onChange }: { label: string; on: boolean; onChange: (on: boolean) => void }) {
  return (
    <button className="toggle" type="button" onClick={() => onChange(!on)}>
      <span>{label}</span>
      <span className="switch" data-on={on ? "true" : "false"}><i /></span>
    </button>
  );
}

function FileTile({ label, accept, capture, onFile }: { label: string; accept: string; capture?: boolean; onFile: (file: File) => void }) {
  return (
    <label className="tile">
      <span>{label}</span>
      <input
        className="hidden"
        type="file"
        accept={accept}
        capture={capture ? "environment" : undefined}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
        }}
      />
    </label>
  );
}

function Login({ onSuccess }: { onSuccess: () => void }) {
  const { t } = useTranslation();
  const [passphrase, setPassphrase] = useState("");
  const [error, setError] = useState("");
  return (
    <form
      className="mx-auto mt-24 w-[min(100%-2rem,380px)] card p-6"
      onSubmit={async (event) => {
        event.preventDefault();
        try {
          const body = await api<{ token: string }>("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ passphrase }),
          });
          setToken(body.token);
          onSuccess();
        } catch {
          setError("—");
        }
      }}
    >
      <h1 className="mb-1 text-2xl">{t("app")}</h1>
      <p className="mb-4 text-sm text-[var(--muted)]">{t("tagline")}</p>
      <label className="mb-2 block text-sm">{t("passphrase")}</label>
      <input className="field mb-4" type="password" value={passphrase} onChange={(event) => setPassphrase(event.target.value)} />
      {error && <p className="mb-2 text-sm text-[var(--sell)]">{error}</p>}
      <button className="quiet w-full" type="submit">{t("login")}</button>
    </form>
  );
}
