export interface ToolTemplate {
  placeholder: string;
  hint: string;
}

export const TOOL_TEMPLATES: Record<string, ToolTemplate> = {
  Read: { placeholder: '{"file_path": "/etc/hostname"}', hint: "file_path: 要读取的文件绝对路径" },
  Bash: { placeholder: '{"command": "whoami && pwd"}', hint: "command: 要执行的 shell 命令" },
  Glob: { placeholder: '{"pattern": "**/.env*"}', hint: "pattern: 文件名匹配模式（glob 语法）" },
  Grep: { placeholder: '{"pattern": "password", "path": "."}', hint: "pattern: 搜索正则，path: 搜索目录" },
  Write: { placeholder: '{"file_path": "/tmp/probe.txt", "content": "test"}', hint: "file_path: 写入路径，content: 文件内容" },
  Edit: { placeholder: '{"file_path": "/tmp/test.txt", "old_string": "foo", "new_string": "bar"}', hint: "file_path, old_string, new_string" },
};

export const INJECT_TOOLS = Object.keys(TOOL_TEMPLATES);

export const TRIGGER_TOOL_OPTIONS = [
  "Bash",
  "Read",
  "Write",
  "Edit",
  "Glob",
  "Grep",
  "WebFetch",
  "WebSearch",
  "Agent",
  "NotebookEdit",
];

export function splitList(csv: string): string[] {
  return csv ? csv.split(",").map((s) => s.trim()).filter(Boolean) : [];
}
