import { banner, card, clear, copyButton, elem, field, jsonTree } from "../components.js";
import { renderGraphView } from "./graph.js";

type ToolCaller = (name: string, args: Record<string, unknown>) => Promise<Record<string, unknown> | null>;

const THREAD_TABS = ["Overview", "Graph", "Checkpoints", "State", "Context", "Memory"] as const;
type ThreadTab = (typeof THREAD_TABS)[number];
const SCOPED_THREAD_TABS: ThreadTab[] = ["Overview", "Graph", "Checkpoints", "State"];

function checkpoints(data: Record<string, unknown>): Record<string, unknown>[] {
  const history = data.history as Record<string, unknown> | undefined;
  return (history?.checkpoints as Record<string, unknown>[] | undefined) ?? [];
}

function checkpointId(item: Record<string, unknown>): string {
  return String(item.checkpoint_id ?? item.id ?? item.checkpoint ?? "(unknown)");
}

function checkpointLabel(item: Record<string, unknown>): string {
  const metadata = (item.metadata as Record<string, unknown> | undefined) ?? {};
  const parts = [
    metadata.step != null ? `step ${String(metadata.step)}` : null,
    metadata.source ? String(metadata.source) : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "checkpoint";
}

function checkpointTime(item: Record<string, unknown>): string {
  const ts = String(item.timestamp ?? "");
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

function hasDiff(diff: unknown): boolean {
  if (!diff || typeof diff !== "object") return false;
  const data = diff as Record<string, unknown>;
  return ["added_keys", "removed_keys", "changed_keys"].some((key) => {
    const value = data[key];
    return Array.isArray(value) && value.length > 0;
  });
}

function truncate(text: unknown, length = 180): string {
  const value = String(text ?? "—");
  return value.length > length ? `${value.slice(0, length)}...` : value;
}

function renderTabButtons(
  active: ThreadTab,
  onTab: (tab: ThreadTab) => void,
  availableTabs: readonly ThreadTab[] = THREAD_TABS,
): HTMLElement {
  const tabList = elem("div", "subtabs");
  for (const tab of availableTabs) {
    const button = elem("button", "subtab", tab);
    button.type = "button";
    button.setAttribute("aria-selected", String(tab === active));
    button.addEventListener("click", () => onTab(tab));
    tabList.appendChild(button);
  }
  return tabList;
}

export function renderThreadView(
  container: HTMLElement,
  data: Record<string, unknown>,
  profile: string,
  callTool: ToolCaller,
  scoped = false,
): void {
  let active: ThreadTab = "Overview";
  let selected: string[] = [];
  let compareResult: Record<string, unknown> | null =
    (data.compare as Record<string, unknown> | undefined) ?? null;
  let checkpointDetail: Record<string, unknown> | null = null;
  let statePayload = (data.state as Record<string, unknown> | undefined) ?? null;
  let contextPayload = (data.context as Record<string, unknown> | undefined) ?? null;
  let memoryPayload = (data.memory as Record<string, unknown> | undefined) ?? null;
  let gapPayload = (data.memory_gaps as Record<string, unknown> | undefined) ?? null;

  const threadId = String(data.thread_id ?? "");

  const rerender = () => {
    clear(container);
    if (!threadId) {
      container.appendChild(banner("err", "Thread Debugger requires a thread_id."));
      return;
    }

    const head = card(scoped ? "Thread" : "Thread Debugger");
    const idLine = elem("div", "id-line");
    idLine.append(elem("span", "row-id", threadId), copyButton(threadId));
    head.appendChild(idLine);
    if (!scoped) {
      head.insertBefore(
        elem("p", "meta", "Inspect checkpoint history, state, and execution flow for this thread."),
        idLine,
      );
    }
    container.append(head, renderTabButtons(active, (tab) => {
      active = tab;
      rerender();
    }, scoped ? SCOPED_THREAD_TABS : THREAD_TABS));

    if (active === "Overview") renderOverview();
    if (active === "Graph") renderGraphView(container, checkpoints(data));
    if (active === "Checkpoints") renderTimeline();
    if (active === "State") renderState();
    if (active === "Context") renderContext();
    if (active === "Memory") renderMemory();
  };

  const renderOverview = () => {
    const summary = (data.summary as Record<string, unknown> | undefined) ?? {};
    const context = contextPayload ?? {};
    const section = card("Overview");
    section.append(
      field("Messages", summary.message_count ?? "unknown"),
      field("Checkpoints", checkpoints(data).length),
      field("Truncated", Boolean(summary.truncated || context.truncated) ? "yes" : "no"),
      field("Last user", truncate(summary.last_user_message)),
      field("Last assistant", truncate(summary.last_assistant_message)),
    );
    if (context.warnings) {
      section.appendChild(banner("warn", `Context warnings: ${String(context.warnings)}`));
    }
    container.appendChild(section);
  };

  const renderTimeline = () => {
    const section = card("Checkpoints");
    const history = data.history as Record<string, unknown> | undefined;
    if (history?.truncated) {
      section.appendChild(
        banner("warn", "Checkpoint history truncated — load more pages or ask the model for full history."),
      );
    }
    const items = checkpoints(data);
    if (items.length === 0) {
      section.appendChild(elem("p", "empty", "No checkpoints found for this thread."));
    }
    for (const item of items) {
      const id = checkpointId(item);
      const row = elem("div", "checkpoint-row");
      const checkbox = elem("input") as HTMLInputElement;
      checkbox.type = "checkbox";
      checkbox.checked = selected.includes(id);
      checkbox.addEventListener("change", () => {
        selected = checkbox.checked
          ? [...selected, id].slice(-2)
          : selected.filter((value) => value !== id);
        rerender();
      });
      const label = elem("button", "link-button", id);
      label.type = "button";
      label.addEventListener("click", async () => {
        checkpointDetail = await callTool("__ui_get_checkpoint", {
          profile,
          thread_id: threadId,
          checkpoint_id: id,
        });
        rerender();
      });
      row.append(checkbox, label, elem("span", "meta", `${item.message_count ?? "?"} messages`));
      const detail = elem("span", "meta", [checkpointLabel(item), checkpointTime(item)].filter(Boolean).join(" · "));
      row.replaceChildren(checkbox, label, detail);
      section.appendChild(row);
    }

    const compare = elem("button", "primary", "Compare selected");
    compare.type = "button";
    compare.disabled = selected.length !== 2;
    compare.addEventListener("click", async () => {
      compareResult = await callTool("__ui_compare_checkpoints", {
        profile,
        thread_id: threadId,
        checkpoint_id_a: selected[0],
        checkpoint_id_b: selected[1],
      });
      rerender();
    });
    section.appendChild(compare);
    if (compareResult) {
      const diff = card("Compare Result");
      const result = compareResult.diff ?? compareResult;
      if (!hasDiff(result)) {
        diff.appendChild(
          banner(
            "warn",
            "No value differences found. These checkpoints may differ only by metadata, parent links, or timing.",
          ),
        );
      }
      diff.appendChild(jsonTree(result));
      section.appendChild(diff);
    }
    if (checkpointDetail) {
      const detail = card("Checkpoint Detail");
      detail.appendChild(jsonTree(checkpointDetail));
      section.appendChild(detail);
    }
    container.appendChild(section);
  };

  const renderState = () => {
    const section = card("State");
    const reload = elem("button", "primary", "Refresh state");
    reload.type = "button";
    reload.addEventListener("click", async () => {
      statePayload = await callTool("__ui_get_thread_state", { profile, thread_id: threadId });
      rerender();
    });
    section.append(reload, jsonTree(statePayload?.state ?? statePayload ?? {}));
    container.appendChild(section);
  };

  const renderContext = () => {
    const section = card("Context");
    const input = elem("input", "filter-input") as HTMLInputElement;
    input.placeholder = "Optional model hint";
    const rerun = elem("button", "primary", "Analyze context");
    rerun.type = "button";
    rerun.addEventListener("click", async () => {
      contextPayload = await callTool("__ui_analyze_context_window", {
        profile,
        thread_id: threadId,
        model_hint: input.value || undefined,
      });
      rerender();
    });
    section.append(input, rerun, jsonTree(contextPayload ?? {}));
    container.appendChild(section);
  };

  const renderMemory = () => {
    const section = card("Memory");
    const user = elem("input", "filter-input") as HTMLInputElement;
    user.placeholder = "User ID";
    const namespace = elem("input", "filter-input") as HTMLInputElement;
    namespace.placeholder = "Expected namespace (optional)";
    const summarize = elem("button", "primary", "Summarize memory");
    summarize.type = "button";
    summarize.addEventListener("click", async () => {
      memoryPayload = await callTool("__ui_summarize_user_memory", {
        profile,
        user_id: user.value,
      });
      rerender();
    });
    const gaps = elem("button", "primary", "Analyze memory gaps");
    gaps.type = "button";
    gaps.addEventListener("click", async () => {
      gapPayload = await callTool("__ui_analyze_memory_gaps", {
        profile,
        thread_id: threadId,
        user_id: user.value,
        expected_namespace: namespace.value || undefined,
      });
      rerender();
    });
    section.append(user, namespace, summarize, gaps);
    if (memoryPayload) {
      const memory = card("Memory Summary");
      memory.appendChild(jsonTree(memoryPayload));
      section.appendChild(memory);
    }
    if (gapPayload) {
      const gapsCard = card("Memory Gap Diagnostics");
      gapsCard.appendChild(jsonTree(gapPayload));
      section.appendChild(gapsCard);
    }
    const advanced = document.createElement("details");
    advanced.className = "card nested";
    advanced.appendChild(elem("summary", undefined, "Advanced store lookup"));
    advanced.appendChild(elem("p", "meta", "Use the model-facing store tools for broad browsing; this panel stays focused on thread diagnosis."));
    section.appendChild(advanced);
    container.appendChild(section);
  };

  rerender();
}
