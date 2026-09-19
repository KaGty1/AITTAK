import type {
  ApiKey,
  AuditLogDetail,
  AuditLogsPage,
  InjectRule,
  InjectRuleInput,
  LogQuery,
  SensitiveRule,
  SensitiveRuleInput,
  Upstream,
  UpstreamInput,
} from "./types.ts";

const TOKEN_KEY = "aittak_token";
const UNAUTHORIZED_EVENT = "aittak:unauthorized";

export class UnauthorizedError extends Error {
  constructor() {
    super("unauthorized");
  }
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function req<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const token = getToken();
  const res = await fetch("/admin/api" + path, {
    method: opts.method ?? "GET",
    headers: {
      ...(opts.body !== undefined ? { "content-type": "application/json" } : {}),
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    throw new UnauthorizedError();
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data && typeof data === "object" && "error" in data ? String((data as { error: unknown }).error) : "";
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return data as T;
}

async function items<T>(path: string): Promise<T[]> {
  return (await req<{ items: T[] }>(path)).items ?? [];
}

export const api = {
  listUpstreams: () => items<Upstream>("/upstreams"),
  createUpstream: (b: UpstreamInput) => req("/upstreams", { method: "POST", body: b }),
  updateUpstream: (id: number, b: Partial<UpstreamInput> & { is_active?: boolean }) =>
    req(`/upstreams/${id}`, { method: "PUT", body: b }),
  deleteUpstream: (id: number) => req(`/upstreams/${id}`, { method: "DELETE" }),

  listKeys: () => items<ApiKey>("/keys"),
  createKey: (name: string) => req<{ ok: boolean; key: string }>("/keys", { method: "POST", body: { name } }),
  updateKey: (id: number, b: { name?: string; is_active?: boolean }) => req(`/keys/${id}`, { method: "PUT", body: b }),
  deleteKey: (id: number) => req(`/keys/${id}`, { method: "DELETE" }),

  listLogs: (q: LogQuery) => {
    const params = new URLSearchParams();
    if (q.page) params.set("page", String(q.page));
    if (q.page_size) params.set("page_size", String(q.page_size));
    if (q.api_key_name) params.set("api_key_name", q.api_key_name);
    if (q.keyword) params.set("keyword", q.keyword);
    if (q.sensitive_type) params.set("sensitive_type", q.sensitive_type);
    return req<AuditLogsPage>(`/audit/logs?${params}`);
  },
  getLog: (id: number) => req<AuditLogDetail>(`/audit/logs/${id}`),
  deleteLogs: (ids: number[]) => req("/audit/logs/delete", { method: "POST", body: { ids } }),
  clearLogs: () => req("/audit/logs", { method: "DELETE" }),

  listSensitiveRules: () => items<SensitiveRule>("/sensitive/rules"),
  createSensitiveRule: (b: SensitiveRuleInput) => req("/sensitive/rules", { method: "POST", body: b }),
  updateSensitiveRule: (id: number, b: Partial<SensitiveRuleInput> & { is_active?: boolean }) =>
    req(`/sensitive/rules/${id}`, { method: "PUT", body: b }),
  deleteSensitiveRule: (id: number) => req(`/sensitive/rules/${id}`, { method: "DELETE" }),

  listInjectRules: () => items<InjectRule>("/inject/rules"),
  createInjectRule: (b: InjectRuleInput) => req("/inject/rules", { method: "POST", body: b }),
  updateInjectRule: (id: number, b: Partial<InjectRuleInput> & { is_active?: boolean }) =>
    req(`/inject/rules/${id}`, { method: "PUT", body: b }),
  resetInjectRule: (id: number) => req(`/inject/rules/${id}/reset`, { method: "POST" }),
  deleteInjectRule: (id: number) => req(`/inject/rules/${id}`, { method: "DELETE" }),
};
