import { useEffect, useState } from "react";
import { Activity, KeyRound, LogOut, Server, ShieldAlert, Syringe, type LucideIcon } from "lucide-react";
import { toast } from "sonner";

import { Login } from "./components/Login.tsx";
import { clearToken, getToken } from "./lib/api.ts";
import { cn } from "./lib/utils.ts";
import { InjectPage } from "./pages/InjectPage.tsx";
import { KeysPage } from "./pages/KeysPage.tsx";
import { MonitorPage } from "./pages/MonitorPage.tsx";
import { SettingsPage } from "./pages/SettingsPage.tsx";
import { UpstreamsPage } from "./pages/UpstreamsPage.tsx";

type View = "monitor" | "upstreams" | "keys" | "inject" | "settings";

const NAV: { view: View; label: string; icon: LucideIcon }[] = [
  { view: "monitor", label: "行为监控", icon: Activity },
  { view: "upstreams", label: "上游配置", icon: Server },
  { view: "keys", label: "API Key", icon: KeyRound },
  { view: "inject", label: "工具注入", icon: Syringe },
  { view: "settings", label: "敏感规则", icon: ShieldAlert },
];

export function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [view, setView] = useState<View>("monitor");

  useEffect(() => {
    const h = () => {
      setAuthed(false);
      toast.error("登录已失效，请重新认证");
    };
    window.addEventListener("aittak:unauthorized", h);
    return () => window.removeEventListener("aittak:unauthorized", h);
  }, []);

  if (!authed) return <Login onSuccess={() => setAuthed(true)} />;

  const logout = () => {
    clearToken();
    setAuthed(false);
  };

  return (
    <div className="flex h-screen">
      <aside className="flex w-52 shrink-0 flex-col gap-1 border-r border-line bg-surface p-3">
        <div className="px-3 pb-4 pt-2 font-display text-lg font-semibold tracking-tight">AITTAK</div>
        {NAV.map(({ view: v, label, icon: Icon }) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition",
              view === v ? "bg-line/70 font-medium text-ink" : "text-muted hover:bg-line/40 hover:text-ink",
            )}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={logout}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-faint transition hover:text-danger"
        >
          <LogOut size={16} /> 退出登录
        </button>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl p-8">
          {view === "monitor" && <MonitorPage />}
          {view === "upstreams" && <UpstreamsPage />}
          {view === "keys" && <KeysPage />}
          {view === "inject" && <InjectPage />}
          {view === "settings" && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}
