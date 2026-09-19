import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() }, Toaster: () => null }));

import { App } from "../App.tsx";
import type { AuditLogDetail, AuditLogsPage, Upstream } from "../lib/types.ts";

interface Call {
  url: string;
  method: string;
  body?: Record<string, unknown>;
  headers: Record<string, string>;
}

let calls: Call[] = [];

function installFetch(route: (url: string, method: string) => unknown) {
  calls = [];
  globalThis.fetch = vi.fn(async (input: unknown, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    const headers = (init?.headers ?? {}) as Record<string, string>;
    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
    calls.push({ url, method, body, headers });
    return {
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => route(url, method),
    } as unknown as Response;
  }) as unknown as typeof fetch;
}

const upstream: Upstream = {
  id: 1, name: "mock-upstream", platform: "claude", base_url: "http://127.0.0.1:1",
  api_key: "mk", is_active: true, created_at: "2025-01-01 00:00:00",
};

const logsPage: AuditLogsPage = {
  items: [{
    id: 1, request_id: "r1", created_at: "2025-01-01 00:00:01", api_key_id: 1,
    api_key_name: "e2e", client_ip: "127.0.0.1", endpoint: "/v1/messages", model: "m",
    upstream_id: 1, user_prompt: "whoami probe", tool_summary: "Bash",
    sensitive_hits: [{ rule_id: 1, rule_name: "手机号", count: 1 }],
    status_code: 200, duration_ms: 12,
  }],
  total: 1, page: 1, page_size: 50,
};

const logDetail: AuditLogDetail = {
  id: 1, request_id: "r1", created_at: "2025-01-01 00:00:01", api_key_id: 1,
  api_key_name: "e2e", client_ip: "127.0.0.1", endpoint: "/v1/messages", model: "m",
  upstream_id: 1, user_prompt: "whoami probe",
  sensitive_hits: [{ rule_id: 1, rule_name: "手机号", count: 1 }],
  status_code: 200, duration_ms: 12,
  tool_calls: [{ tool_name: "Bash", tool_use_id: "t1", input: '{"command":"whoami"}', result: "root" }],
};

function route(url: string, method: string): unknown {
  if (url.startsWith("/admin/api/audit/logs/")) return logDetail;
  if (url.startsWith("/admin/api/audit/logs")) return logsPage;
  if (url.startsWith("/admin/api/upstreams")) {
    if (method === "POST") return { ok: true };
    return { items: [upstream] };
  }
  if (url.startsWith("/admin/api/keys")) return { items: [] };
  if (url.startsWith("/admin/api/sensitive/rules")) return { items: [] };
  if (url.startsWith("/admin/api/inject/rules")) return { items: [] };
  throw new Error(`unexpected ${method} ${url}`);
}

async function login() {
  await userEvent.type(screen.getByPlaceholderText("ADMIN_PASSWORD"), "pw");
  await userEvent.click(screen.getByRole("button", { name: "登录" }));
  await screen.findByRole("heading", { name: "行为监控" });
}

describe("AITTAK console", () => {
  beforeEach(() => {
    localStorage.clear();
    installFetch(route);
  });

  it("login sends bearer and renders monitor table", async () => {
    render(<App />);
    await login();
    expect(calls[0].url).toBe("/admin/api/upstreams");
    expect(calls[0].headers["authorization"]).toBe("Bearer pw");
    expect(await screen.findByText("whoami probe")).toBeInTheDocument();
    expect(screen.getByText("Bash")).toBeInTheDocument();
    expect(screen.getByText("手机号")).toBeInTheDocument();
  });

  it("monitor row click opens detail modal with tool calls", async () => {
    render(<App />);
    await login();
    await userEvent.click(await screen.findByText("whoami probe"));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("请求详情")).toBeInTheDocument();
    expect(within(dialog).getByText("Bash")).toBeInTheDocument();
    expect(within(dialog).getByText(/"command": "whoami"/)).toBeInTheDocument();
    expect(within(dialog).getByText("root")).toBeInTheDocument();
    expect(calls.some((c) => c.url === "/admin/api/audit/logs/1")).toBe(true);
  });

  it("upstream create roundtrip posts payload", async () => {
    render(<App />);
    await login();
    await userEvent.click(screen.getByRole("button", { name: /上游配置/ }));
    await screen.findByText("mock-upstream");
    await userEvent.click(screen.getByRole("button", { name: /添加上游/ }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("名称"), "new-up");
    await userEvent.type(within(dialog).getByLabelText(/API Key/), "sk-new");
    await userEvent.click(within(dialog).getByRole("button", { name: "保存" }));
    const post = await waitFor(() => calls.find((c) => c.method === "POST" && c.url === "/admin/api/upstreams"));
    expect(post?.body).toMatchObject({ name: "new-up", platform: "claude", api_key: "sk-new" });
  });

  it("401 clears token and stays on login", async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: false,
      status: 401,
      headers: { get: () => "application/json" },
      json: async () => ({}),
    }) as unknown as Response) as unknown as typeof fetch;
    render(<App />);
    await userEvent.type(screen.getByPlaceholderText("ADMIN_PASSWORD"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "登录" }));
    await screen.findByText("密码错误");
    expect(localStorage.getItem("aittak_token")).toBeNull();
  });
});
