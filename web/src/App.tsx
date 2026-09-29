import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { api, setToken, token } from "./api";
import { applyDirection } from "./i18n";
import { Approvals, Activity, Agents, ChartPage, Chat, Dashboard, Debate, Journal, Lessons, News, Reports, Rules, Settings, Signals, Skills } from "./screens";

const links = [
  ["/", "nav.dashboard"],
  ["/chat", "nav.chat"],
  ["/activity", "nav.activity"],
  ["/agents", "nav.tree"],
  ["/debate", "nav.debate"],
  ["/chart", "nav.charts"],
  ["/signals", "nav.signals"],
  ["/approvals", "nav.approvals"],
  ["/skills", "nav.skills"],
  ["/rules", "nav.rules"],
  ["/news", "nav.news"],
  ["/journal", "nav.journal"],
  ["/lessons", "nav.lessons"],
  ["/reports", "nav.reports"],
  ["/settings", "nav.settings"],
] as const;

export default function App() {
  const { t, i18n } = useTranslation();
  const [authed, setAuthed] = useState(Boolean(token()));
  const navigate = useNavigate();

  useEffect(() => {
    applyDirection(i18n.language);
  }, [i18n.language]);

  if (!authed) {
    return <Login onSuccess={() => { setAuthed(true); navigate("/"); }} />;
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[220px_1fr]">
      <aside className="border-b border-[var(--line)] bg-[var(--surface)] p-4 md:border-b-0 md:border-e">
        <div className="mb-4">
          <div className="text-lg font-semibold text-[var(--gold)]">{t("app")}</div>
          <div className="text-xs text-[var(--muted)]">{t("tagline")}</div>
        </div>
        <nav className="flex max-w-full gap-2 overflow-x-auto md:flex-col">
          {links.map(([path, key]) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              className={({ isActive }) =>
                `rounded-full px-3 py-2 text-sm whitespace-nowrap ${isActive ? "bg-[var(--card)] text-[var(--gold)]" : "text-[var(--muted)]"}`
              }
            >
              {t(key)}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 p-4 md:p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/debate" element={<Debate />} />
          <Route path="/chart" element={<ChartPage />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/news" element={<News />} />
          <Route path="/journal" element={<Journal />} />
          <Route path="/lessons" element={<Lessons />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

function Login({ onSuccess }: { onSuccess: () => void }) {
  const { t } = useTranslation();
  const [passphrase, setPassphrase] = useState("");
  const [error, setError] = useState("");
  return (
    <form
      className="mx-auto mt-24 w-[min(100%-2rem,380px)] rounded-[var(--radius)] border border-[var(--line)] bg-[var(--card)] p-6 shadow-[var(--shadow)]"
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
      <h1 className="mb-1 text-2xl text-[var(--gold)]">{t("app")}</h1>
      <p className="mb-4 text-sm text-[var(--muted)]">{t("tagline")}</p>
      <label className="mb-2 block text-sm">{t("passphrase")}</label>
      <input
        className="mb-4 w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3 py-2"
        type="password"
        value={passphrase}
        onChange={(event) => setPassphrase(event.target.value)}
      />
      {error && <p className="mb-2 text-sm text-[var(--sell)]">{error}</p>}
      <button className="w-full rounded-lg bg-[var(--gold)] px-3 py-2 font-medium text-black" type="submit">
        {t("login")}
      </button>
    </form>
  );
}
