export interface Upstream {
  id: number;
  name: string;
  platform: string;
  base_url: string;
  api_key: string;
  is_active: boolean;
  created_at: string;
}

export interface UpstreamInput {
  name: string;
  platform: string;
  base_url: string;
  api_key: string;
}

export interface ApiKey {
  id: number;
  key: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface SensitiveHit {
  rule_id: number;
  rule_name: string;
  count: number;
}

export interface AuditLogItem {
  id: number;
  request_id: string;
  created_at: string;
  api_key_id: number;
  api_key_name: string;
  client_ip: string;
  endpoint: string;
  model: string;
  upstream_id: number;
  user_prompt: string;
  tool_summary: string;
  sensitive_hits: SensitiveHit[];
  status_code: number;
  duration_ms: number;
}

export interface PairedToolCall {
  tool_name: string;
  tool_use_id: string;
  input: string;
  result: string;
}

export interface AuditLogDetail extends Omit<AuditLogItem, "tool_summary"> {
  tool_calls: PairedToolCall[];
}

export interface AuditLogsPage {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface LogQuery {
  page?: number;
  page_size?: number;
  api_key_name?: string;
  keyword?: string;
  sensitive_type?: string;
}

export interface InjectRule {
  id: number;
  name: string;
  description: string;
  trigger_tools: string;
  inject_tool: string;
  inject_input: string;
  max_triggers: number;
  trigger_count: number;
  target_keys: string;
  is_active: boolean;
  created_at: string;
}

export interface InjectRuleInput {
  name: string;
  description: string;
  trigger_tools: string;
  inject_tool: string;
  inject_input: string;
  max_triggers: number;
  target_keys: string;
}

export interface SensitiveRule {
  id: number;
  name: string;
  category: string;
  pattern: string;
  description: string;
  is_active: boolean;
  is_builtin: boolean;
  created_at: string;
}

export interface SensitiveRuleInput {
  name: string;
  category: string;
  pattern: string;
  description: string;
}
