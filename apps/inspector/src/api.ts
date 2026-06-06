import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import type { App } from "@modelcontextprotocol/ext-apps";

export function parseToolJson(result: CallToolResult | undefined): Record<string, unknown> | null {
  if (!result) return null;
  const structured = result.structuredContent;
  if (structured && typeof structured === "object") {
    return structured as Record<string, unknown>;
  }
  const text = result.content?.find((c) => c.type === "text")?.text;
  if (!text) return null;
  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export async function callUiTool(
  app: App,
  name: string,
  args: Record<string, unknown>,
): Promise<Record<string, unknown> | null> {
  const result = await app.callServerTool({ name, arguments: args });
  return parseToolJson(result);
}

/** LangMCP list_threads returns `threads`; older UI mocks used `thread_ids`. */
export function extractThreadIds(data: Record<string, unknown>): string[] {
  const ids = data.thread_ids;
  if (Array.isArray(ids)) {
    return ids.filter((id): id is string => typeof id === "string" && id.length > 0);
  }
  const rows = data.threads;
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row) => {
      if (typeof row === "string") return row;
      if (row && typeof row === "object" && "thread_id" in row) {
        return String((row as { thread_id: unknown }).thread_id);
      }
      return "";
    })
    .filter((id) => id.length > 0);
}

export function threadLastUpdated(
  data: Record<string, unknown>,
  threadId: string,
): string | undefined {
  const rows = data.threads;
  if (!Array.isArray(rows)) return undefined;
  for (const row of rows) {
    if (row && typeof row === "object" && (row as { thread_id?: string }).thread_id === threadId) {
      const ts = (row as { last_updated?: unknown }).last_updated;
      return typeof ts === "string" ? ts : undefined;
    }
  }
  return undefined;
}
