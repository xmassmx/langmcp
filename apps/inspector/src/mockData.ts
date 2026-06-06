import type { InspectorPayload, InspectorView } from "./types.js";

const profiles = {
  profiles: [
    {
      name: "dev",
      checkpointer_backend: "postgres",
      store_backend: "postgres",
      has_store: "true",
    },
    {
      name: "local_sqlite",
      checkpointer_backend: "sqlite",
      store_backend: "none",
      has_store: "false",
    },
    {
      name: "broken_redis",
      checkpointer_backend: "redis",
      store_backend: "none",
      has_store: "false",
    },
  ],
  active_profile: "dev",
  profile: "dev",
  truncated: false,
};

const healthChecks = [
  {
    profile: "dev",
    checkpointer_connected: true,
    store_connected: true,
    checkpointer_setup: false,
    store_setup: false,
    checkpointer_backend: "postgres",
    store_backend: "postgres",
    checkpointer_uri_redacted: "postgresql://langgraph:***@localhost:5442/langgraph",
    store_uri_redacted: "postgresql://langgraph:***@localhost:5442/langgraph",
    read_only: true,
    has_store: true,
    warning: null,
    truncated: false,
  },
  {
    profile: "local_sqlite",
    checkpointer_connected: true,
    store_connected: null,
    checkpointer_setup: false,
    store_setup: null,
    checkpointer_backend: "sqlite",
    store_backend: null,
    checkpointer_uri_redacted: "sqlite:////tmp/langmcp-demo.sqlite",
    store_uri_redacted: null,
    read_only: true,
    has_store: false,
    warning: null,
    truncated: false,
  },
  {
    profile: "broken_redis",
    checkpointer_connected: false,
    store_connected: null,
    checkpointer_setup: false,
    store_setup: null,
    checkpointer_backend: "redis",
    store_backend: null,
    checkpointer_uri_redacted: "redis://localhost:6379/0",
    store_uri_redacted: null,
    read_only: true,
    has_store: false,
    warning: "Connection refused while probing checkpointer",
    truncated: false,
  },
];

const threadIds = [
  "8f3a7b7f-15c3-41a5-8e84-18d09db31c21",
  "9b12f522-e421-4e25-84da-95566f690004",
  "a43ddf54-52a5-4a1f-a037-6f7cba042600",
  "dev-thread-customer-support-long-context",
  "memory-regression-repro-issue-7",
  "checkout-agent-2026-06-03",
  "qa-thread-empty-store",
  "redis-thread-with-truncated-history",
];

const checkpointHistory = {
  thread_id: threadIds[1],
  checkpoints: [
    { checkpoint_id: "cp_9f2_latest", message_count: 12, ts: "2026-06-03T14:02:00Z" },
    { checkpoint_id: "cp_8a1_tool", message_count: 10, ts: "2026-06-03T13:58:00Z" },
    { checkpoint_id: "cp_7c0_start", message_count: 8, ts: "2026-06-03T13:52:00Z" },
  ],
  page: 1,
  total_pages: 1,
  total_items: 3,
  profile: "dev",
  truncated: false,
};

const threadSeed = {
  profiles,
  thread_id: threadIds[1],
  summary: {
    thread_id: threadIds[1],
    message_count: 12,
    last_user_message: "Why did the agent forget the user's preferred theme?",
    last_assistant_message: "I checked the checkpoint state and memory namespace.",
    transcript: [
      { role: "user", content: "Please remember that I prefer dark mode." },
      { role: "assistant", content: "Saved your preference." },
      { role: "user", content: "Why did the next run use light mode?" },
    ],
    page: 1,
    total_pages: 1,
    profile: "dev",
    truncated: false,
  },
  history: checkpointHistory,
  state: {
    thread_id: threadIds[1],
    state: {
      config: { configurable: { thread_id: threadIds[1], user_id: "alice" } },
      metadata: { source: "dummy-preview" },
      values: {
        messages: [
          { type: "human", content: "Please remember that I prefer dark mode." },
          { type: "ai", content: "Saved your preference." },
        ],
        user_preferences: { theme: "dark" },
      },
    },
    profile: "dev",
    truncated: false,
  },
  context: {
    thread_id: threadIds[1],
    token_estimate: 3120,
    warnings: ["Thread has 64 messages (>50). Consider summarization."],
    channels: { messages: 2800, user_preferences: 120, metadata: 200 },
    profile: "dev",
    truncated: false,
  },
  memory: {
    user_id: "alice",
    item_count: 2,
    useful_facts: ["Prefers dark mode", "Uses PostgreSQL checkpointer in dev"],
    risky_facts: [],
    namespace_anomalies: [],
    profile: "dev",
    truncated: false,
  },
  memory_gaps: {
    thread_id: threadIds[1],
    user_id: "alice",
    verdict: "Likely namespace mismatch",
    evidence: ["Thread configurable user_id is alice", "Store search found facts under users/alice"],
    next_action: "Check expected namespace mapping in the application.",
    profile: "dev",
    truncated: false,
  },
};

export function buildMockPayload(view: InspectorView): InspectorPayload {
  if (view === "thread") {
    return {
      view,
      profile: "dev",
      read_only: true,
      errors: [],
      seed: threadSeed,
    };
  }

  if (view === "threads") {
    return {
      view,
      profile: "dev",
      read_only: true,
      errors: [],
      seed: {
        profiles,
        threads: {
          thread_ids: threadIds,
          total: 23,
          limit: 8,
          offset: 0,
          truncated: true,
          profile: "dev",
        },
      },
    };
  }

  return {
    view: "health",
    profile: "dev",
    read_only: true,
    errors: [],
    seed: {
      profiles,
      health_checks: healthChecks,
    },
  };
}

export function buildMockToolResult(name: string, args: Record<string, unknown>): Record<string, unknown> | null {
  if (name === "show_inspector") {
    return buildMockPayload((args.view as InspectorView | undefined) ?? "health");
  }

  if (name === "__ui_list_threads") {
    const offset = Number(args.offset ?? 0);
    const limit = Number(args.limit ?? 8);
    const more = Array.from({ length: limit }, (_, index) => {
      const n = offset + index + 1;
      return `dummy-thread-page-${String(n).padStart(2, "0")}`;
    });
    return {
      thread_ids: more,
      total: 23,
      limit,
      offset,
      truncated: offset + limit < 23,
      profile: String(args.profile ?? "dev"),
    };
  }

  if (name === "__ui_get_checkpoint") {
    return {
      thread_id: String(args.thread_id),
      checkpoint_id: String(args.checkpoint_id),
      state: threadSeed.state.state,
      profile: String(args.profile ?? "dev"),
      truncated: false,
    };
  }

  if (name === "__ui_get_thread_state") {
    return threadSeed.state;
  }

  if (name === "__ui_analyze_context_window") {
    return threadSeed.context;
  }

  if (name === "__ui_compare_checkpoints") {
    return {
      thread_id: String(args.thread_id),
      checkpoint_id_a: String(args.checkpoint_id_a),
      checkpoint_id_b: String(args.checkpoint_id_b),
      diff: {
        changed: ["messages", "user_preferences.theme"],
        added: ["memory_write"],
        removed: [],
        unchanged: ["metadata", "configurable.thread_id"],
      },
      profile: String(args.profile ?? "dev"),
      truncated: false,
    };
  }

  if (name === "__ui_summarize_user_memory") {
    return threadSeed.memory;
  }

  if (name === "__ui_analyze_memory_gaps") {
    return threadSeed.memory_gaps;
  }

  return null;
}
