import type { HealthRow, ProfileRow } from "../types.js";

function statusClass(row: HealthRow): string {
  if (row.error && typeof row.error === "object" && row.error.code === "backend_unreachable") {
    return "err";
  }
  if (row.checkpointer_connected === false) return "err";
  if (row.warning) return "warn";
  if (row.checkpointer_connected) return "ok";
  return "warn";
}

export function renderHealthView(
  container: HTMLElement,
  profiles: ProfileRow[],
  healthChecks: HealthRow[],
  activeProfile: string,
  onRefresh?: () => void,
): void {
  container.innerHTML = "";

  const card = document.createElement("section");
  card.className = "card";
  card.innerHTML = `<h2>Profiles</h2>`;

  const byName = new Map(healthChecks.map((h) => [h.profile ?? "", h]));

  for (const profile of profiles) {
    const health = byName.get(profile.name);
    const row = document.createElement("div");
    row.className = "row";
    row.style.cursor = "default";

    const dot = document.createElement("span");
    dot.className = `status-dot ${health ? statusClass(health) : "warn"}`;
    row.appendChild(dot);

    const body = document.createElement("div");
    body.style.flex = "1";
    const nameLine = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = profile.name;
    nameLine.appendChild(name);
    if (profile.name === activeProfile) {
      nameLine.append(" · active");
    }

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${profile.checkpointer_backend} · store ${profile.store_backend}`;

    body.append(nameLine, meta);
    row.appendChild(body);

    if (health?.warning) {
      const warn = document.createElement("div");
      warn.className = "meta";
      warn.textContent = health.warning;
      warn.style.marginTop = "4px";
      body.appendChild(warn);
    }

    card.appendChild(row);
  }

  container.appendChild(card);

  const active = document.createElement("section");
  active.className = "card";
  const check = byName.get(activeProfile);
  active.innerHTML = `<h2>Active profile</h2>`;
  if (check) {
    const pre = document.createElement("pre");
    pre.className = "meta";
    pre.style.margin = "0";
    pre.style.whiteSpace = "pre-wrap";
    pre.textContent = [
      `Checkpointer: ${check.checkpointer_connected ? "connected" : "disconnected"}`,
      check.store_connected != null ? `Store: ${check.store_connected ? "connected" : "disconnected"}` : "Store: n/a",
      check.checkpointer_uri_redacted ? `URI: ${String(check.checkpointer_uri_redacted)}` : "",
    ]
      .filter(Boolean)
      .join("\n");
    active.appendChild(pre);
  } else {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = `No health data for ${activeProfile}`;
    active.appendChild(empty);
  }
  container.appendChild(active);
  if (onRefresh) {
    const refresh = document.createElement("button");
    refresh.type = "button";
    refresh.className = "primary";
    refresh.textContent = "Refresh";
    refresh.addEventListener("click", onRefresh);
    container.appendChild(refresh);
  }
}
