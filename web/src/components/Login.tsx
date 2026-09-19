import { useState } from "react";
import { toast } from "sonner";

import { api, clearToken, getToken, setToken } from "../lib/api.ts";
import { Button } from "./ui/Button.tsx";
import { Field, inputCls } from "./ui/Field.tsx";

export function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!password || busy) return;
    setBusy(true);
    setError("");
    setToken(password);
    try {
      await api.listUpstreams();
      onSuccess();
    } catch {
      clearToken();
      setError("密码错误");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid h-screen place-items-center bg-paper">
      <div className="w-80 rounded-xl border border-line bg-surface p-8 shadow-card">
        <h1 className="font-display text-lg font-semibold">AITTAK</h1>
        <p className="mt-1 mb-6 text-sm text-faint">红队 AI 中转站 · 管理控制台</p>
        <Field label="管理员密码">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder={getToken() ? "" : "ADMIN_PASSWORD"}
            className={inputCls}
            autoFocus
          />
        </Field>
        <Button variant="primary" className="w-full justify-center" onClick={submit} disabled={busy}>
          {busy ? "验证中…" : "登录"}
        </Button>
        {error && (
          <p className="mt-3 text-center text-xs text-danger" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
