import { App } from "@modelcontextprotocol/ext-apps";
import { callUiTool, extractThreadIds, parseToolJson } from "./api.js";
import { buildMockPayload, buildMockToolResult } from "./mockData.js";
import type { HostContext, InspectorError, InspectorPayload, InspectorView, ProfileRow } from "./types.js";
import { renderHealthView } from "./views/health.js";
import { renderThreadView } from "./views/thread.js";
import { renderThreadsView } from "./views/threads.js";

const VIEWS: InspectorView[] = ["health", "threads"];
const VIEW_LABELS: Record<InspectorView, string> = {
  health: "Health",
  threads: "Threads",
  thread: "Thread",
  compare: "Compare",
  memory: "Memory",
};

const headerEl = document.getElementById("header")!;
const tabsEl = document.getElementById("tabs")!;
const mainEl = document.getElementById("main")!;

const app = new App({ name: "LangMCP Inspector", version: "0.1.0" });
const params = new URLSearchParams(window.location.search);
const mockView = params.get("mock") as InspectorView | null;
const useMockData = mockView === "health" || mockView === "threads" || mockView === "thread";
const themeQuery = window.matchMedia("(prefers-color-scheme: light)");
const themeStorageKey = "langmcp-inspector-theme";
const supportedSchemaVersion = 1;

let payload: InspectorPayload | null = null;
let hostThemeActive = false;
let schemaWarningShown = false;
const threadPageSize = 50;
type ThemeChoice = "system" | "dark" | "light";

function savedThemeChoice(): ThemeChoice {
  const value = localStorage.getItem(themeStorageKey);
  return value === "dark" || value === "light" ? value : "system";
}

function resolvedTheme(choice = savedThemeChoice()): "dark" | "light" {
  return choice === "system" ? (themeQuery.matches ? "light" : "dark") : choice;
}

function applyTheme(choice = savedThemeChoice()): void {
  document.documentElement.dataset.theme = resolvedTheme(choice);
  document.documentElement.dataset.themeChoice = choice;
}

let themeToggleSync: (() => void) | null = null;

applyTheme();
themeQuery.addEventListener("change", () => {
  if (savedThemeChoice() === "system") {
    applyTheme("system");
    themeToggleSync?.();
  }
});

function isScopedToolResult(data: Record<string, unknown>): boolean {
  return !("view" in data) && Array.isArray(data.threads);
}

function payloadFromToolResult(data: Record<string, unknown>): InspectorPayload {
  if (isScopedToolResult(data)) {
    return {
      view: "threads",
      profile: String(data.profile ?? "default"),
      read_only: Boolean(data.read_only ?? true),
      scope: "tool",
      errors: [],
      seed: {
        threads: data,
      },
    };
  }
  return data as unknown as InspectorPayload;
}

function setLoading(on: boolean): void {
  if (on) {
    mainEl.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
  }
}

function profileNames(): string[] {
  if (!payload) return [];
  const profiles = (payload.seed.profiles as { profiles?: ProfileRow[] })?.profiles ?? [];
  return profiles.length ? profiles.map((p) => p.name) : [payload.profile];
}

const THEME_ICONS = {
  light: `<svg class="theme-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><circle cx="10" cy="10" r="3.25"/><path stroke-linecap="round" d="M10 2.5v2M10 15.5v2M2.5 10h2M15.5 10h2M4.4 4.4l1.4 1.4M14.2 14.2l1.4 1.4M4.4 15.6l1.4-1.4M14.2 5.8l1.4-1.4"/></svg>`,
  dark: `<svg class="theme-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M15.5 11.2a6.25 6.25 0 1 1-6.7-9.8 7.25 7.25 0 0 0 6.7 9.8z"/></svg>`,
} as const;

function applyHostContext(ctx: HostContext): void {
  const insets = ctx.safeAreaInsets;
  if (insets) {
    const root = document.documentElement;
    root.style.setProperty("--host-safe-top", `${insets.top ?? 0}px`);
    root.style.setProperty("--host-safe-right", `${insets.right ?? 0}px`);
    root.style.setProperty("--host-safe-bottom", `${insets.bottom ?? 0}px`);
    root.style.setProperty("--host-safe-left", `${insets.left ?? 0}px`);
  }

  if (ctx.theme === "light" || ctx.theme === "dark") {
    hostThemeActive = true;
    document.documentElement.dataset.theme = ctx.theme;
    document.documentElement.dataset.themeSource = "host";
    themeToggleSync?.();
    return;
  }

  hostThemeActive = false;
  delete document.documentElement.dataset.themeSource;
  applyTheme();
}

function renderThemeToggle(container: HTMLElement): void {
  const group = document.createElement("div");
  group.className = "theme-toggle";
  group.hidden = hostThemeActive;
  group.setAttribute("role", "group");
  group.setAttribute("aria-label", "Theme");

  const sun = document.createElement("button");
  sun.type = "button";
  sun.className = "theme-toggle-btn";
  sun.innerHTML = THEME_ICONS.light;
  sun.title = "Light theme";
  sun.setAttribute("aria-label", "Light theme");

  const moon = document.createElement("button");
  moon.type = "button";
  moon.className = "theme-toggle-btn";
  moon.innerHTML = THEME_ICONS.dark;
  moon.title = "Dark theme";
  moon.setAttribute("aria-label", "Dark theme");

  const syncPressed = () => {
    const choice = savedThemeChoice();
    const active = choice === "system" ? resolvedTheme() : choice;
    sun.setAttribute("aria-pressed", String(active === "light"));
    moon.setAttribute("aria-pressed", String(active === "dark"));
    group.dataset.system = String(choice === "system");
  };

  sun.addEventListener("click", () => {
    localStorage.setItem(themeStorageKey, "light");
    applyTheme("light");
    syncPressed();
  });
  moon.addEventListener("click", () => {
    localStorage.setItem(themeStorageKey, "dark");
    applyTheme("dark");
    syncPressed();
  });

  syncPressed();
  themeToggleSync = syncPressed;

  group.append(sun, moon);
  container.appendChild(group);
}

function renderProfileChip(container: HTMLElement, name: string): void {
  const chip = document.createElement("span");
  chip.className = "profile-chip";
  chip.title = `Profile: ${name}`;
  const label = document.createElement("span");
  label.className = "profile-chip-label";
  label.textContent = "Profile";
  const value = document.createElement("span");
  value.className = "profile-chip-value";
  value.textContent = name;
  chip.append(label, value);
  container.appendChild(chip);
}

function renderProfileSelect(container: HTMLElement, names: string[]): void {
  const field = document.createElement("label");
  field.className = "header-field";
  const label = document.createElement("span");
  label.className = "header-field-label";
  label.textContent = "Profile";
  const select = document.createElement("select");
  select.className = "profile-select";
  for (const name of names) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    opt.selected = name === payload!.profile;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => void refreshView(payload!.view, select.value, routeArgs()));
  field.append(label, select);
  container.appendChild(field);
}

function renderHeader(): void {
  if (!payload) return;
  headerEl.innerHTML = "";

  const title = document.createElement("span");
  title.className = "header-title";
  title.textContent = payload.scope === "tool" ? VIEW_LABELS[payload.view] : `LangMCP · ${VIEW_LABELS[payload.view]}`;
  headerEl.appendChild(title);

  const actions = document.createElement("div");
  actions.className = "header-actions";

  const names = profileNames();
  const scoped = payload.scope === "tool";
  if (scoped && names.length <= 1) {
    renderProfileChip(actions, payload.profile);
  } else {
    renderProfileSelect(actions, names);
  }

  renderThemeToggle(actions);

  headerEl.appendChild(actions);
}

function renderTabs(): void {
  if (!payload) return;
  tabsEl.innerHTML = "";
  tabsEl.hidden = payload.scope === "tool";
  if (tabsEl.hidden) return;
  for (const view of VIEWS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tab";
    btn.textContent = VIEW_LABELS[view];
    btn.setAttribute("role", "tab");
    btn.setAttribute("aria-selected", String(view === payload!.view));
    btn.addEventListener("click", () => void refreshView(view, payload!.profile));
    tabsEl.appendChild(btn);
  }
}

function formatError(error: InspectorError): string {
  if (typeof error === "string") return error;
  return error.message;
}

function showErrors(errors: InspectorError[]): void {
  for (const error of errors) {
    const msg = formatError(error);
    const code = typeof error === "object" ? error.code : undefined;
    const banner = document.createElement("div");
    banner.className = code === "backend_unreachable" ? "banner err connection-error" : "banner err";
    banner.textContent = code === "backend_unreachable" ? `Connection error: ${msg}` : msg;
    mainEl.prepend(banner);
  }
}

function warnUnknownSchema(version: number | undefined): void {
  if (schemaWarningShown || version == null || version === supportedSchemaVersion) return;
  schemaWarningShown = true;
  console.warn(`LangMCP Inspector: unsupported schema_version ${version}`);
}

function applyPayload(data: InspectorPayload): void {
  payload = data;
  warnUnknownSchema(data.schema_version);
  document.body.classList.toggle("tool-scope", data.scope === "tool");
  renderHeader();
  renderTabs();
  mainEl.innerHTML = "";
  showErrors(data.errors);

  if (data.view === "health") {
    const profiles = (data.seed.profiles as { profiles?: ProfileRow[] })?.profiles ?? [];
    const checks = (data.seed.health_checks as Record<string, unknown>[]) ?? [];
    renderHealthView(mainEl, profiles, checks, data.profile, () => {
      void refreshView("health", data.profile);
    });
    return;
  }

  if (data.view === "threads") {
    const threads = (data.seed.threads as Record<string, unknown>) ?? {};
    renderThreadsView(
      mainEl,
      threads,
      (threadId) => {
        void openThreadFromList(threadId);
      },
      () => void loadMoreThreads(),
    );
    return;
  }

  if (data.view === "thread") {
    renderThreadView(mainEl, data.seed, data.profile, callInspectorTool, data.scope === "tool");
  }
}

async function openThreadFromList(threadId: string): Promise<void> {
  if (!payload) return;
  if (payload.scope !== "tool") {
    await refreshView("thread", payload.profile, { thread_id: threadId });
    return;
  }

  setLoading(true);
  const [summary, history, state] = await Promise.all([
    callInspectorTool("__ui_summarize_thread", { profile: payload.profile, thread_id: threadId }),
    callInspectorTool("__ui_list_checkpoint_history", {
      profile: payload.profile,
      thread_id: threadId,
      limit: 40,
    }),
    callInspectorTool("__ui_get_thread_state", { profile: payload.profile, thread_id: threadId }),
  ]);
  setLoading(false);
  applyPayload({
    view: "thread",
    profile: payload.profile,
    read_only: payload.read_only,
    scope: "tool",
    errors: [],
    seed: {
      thread_id: threadId,
      summary,
      history,
      state,
    },
  });
}

function routeArgs(): Record<string, unknown> {
  if (!payload || payload.view !== "thread") return {};
  return {
    thread_id: payload.seed.thread_id,
  };
}

async function callInspectorTool(
  name: string,
  args: Record<string, unknown>,
): Promise<Record<string, unknown> | null> {
  return useMockData ? buildMockToolResult(name, args) : callUiTool(app, name, args);
}

async function refreshView(
  view: InspectorView,
  profile: string,
  args: Record<string, unknown> = {},
): Promise<void> {
  setLoading(true);
  const result = await callInspectorTool("show_inspector", { view, profile, ...args });
  setLoading(false);
  if (!result) {
    mainEl.innerHTML = '<div class="banner err">Failed to refresh inspector.</div>';
    return;
  }
  applyPayload(result as unknown as InspectorPayload);
}

async function loadMoreThreads(): Promise<void> {
  if (!payload) return;
  const current = (payload.seed.threads as Record<string, unknown>) ?? {};
  const existing = extractThreadIds(current);
  const offset = Number(current.offset ?? 0) + existing.length;
  setLoading(true);
  const args = {
    profile: payload.profile,
    limit: threadPageSize,
    offset,
  };
  const extra = await callInspectorTool("__ui_list_threads", args);
  setLoading(false);
  if (!extra || !payload) return;
  const pageIds = extractThreadIds(extra);
  const seen = new Set(existing);
  const mergedIds = [...existing, ...pageIds.filter((id) => !seen.has(id))];
  payload.seed.threads = {
    ...current,
    ...extra,
    thread_ids: mergedIds,
    threads: undefined,
  };
  applyPayload(payload);
}

function ingestToolResult(result: Parameters<NonNullable<typeof app.ontoolresult>>[0]): void {
  const parsed = parseToolJson(result);
  if (!parsed) {
    mainEl.innerHTML = '<div class="banner err">Invalid inspector payload from host.</div>';
    return;
  }
  applyPayload(payloadFromToolResult(parsed));
}

app.ontoolresult = ingestToolResult;

const hostContextHandler = (ctx: HostContext) => applyHostContext(ctx);
app.onhostcontextchanged = hostContextHandler;
const initialHostContext = (app as { getHostContext?: () => HostContext | undefined }).getHostContext?.();
if (initialHostContext) applyHostContext(initialHostContext);

if (useMockData) {
  applyPayload(buildMockPayload(mockView));
} else {
  app.connect();
}
