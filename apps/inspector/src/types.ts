export type InspectorView = "health" | "threads" | "thread" | "compare" | "memory";

export interface InspectorErrorObject {
  code?: string;
  message: string;
  tool?: string;
}

export type InspectorError = string | InspectorErrorObject;

export interface InspectorPayload {
  schema_version?: number;
  view: InspectorView;
  profile: string;
  read_only: boolean;
  seed: Record<string, unknown>;
  errors: InspectorError[];
  scope?: "inspector" | "tool";
}

export interface HostContext {
  theme?: "light" | "dark";
  safeAreaInsets?: {
    top?: number;
    right?: number;
    bottom?: number;
    left?: number;
  };
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
