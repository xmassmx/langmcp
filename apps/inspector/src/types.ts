export type InspectorView = "health" | "threads" | "thread" | "compare" | "memory";

export interface InspectorPayload {
  view: InspectorView;
  profile: string;
  read_only: boolean;
  seed: Record<string, unknown>;
  errors: string[];
  scope?: "inspector" | "tool";
}

export interface ProfileRow {
  name: string;
  checkpointer_backend: string;
  store_backend: string;
  has_store: string;
}

export interface HealthRow extends Record<string, unknown> {
  profile?: string;
  checkpointer_connected?: boolean;
  store_connected?: boolean | null;
  checkpointer_backend?: string;
  store_backend?: string | null;
  warning?: string | null;
  error?: { code?: string; message?: string } | string | null;
}
