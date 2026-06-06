import { extractThreadIds, threadLastUpdated } from "../api.js";

export function renderThreadsView(
  container: HTMLElement,
  data: Record<string, unknown>,
  onSelect: (threadId: string) => void,
  onLoadMore: () => void,
): void {
  container.innerHTML = "";

  const filter = document.createElement("input");
  filter.type = "search";
  filter.className = "filter-input";
  filter.placeholder = "Filter by thread id prefix";
  filter.setAttribute("aria-label", "Filter threads");
  container.appendChild(filter);

  const list = document.createElement("section");
  list.className = "card";
  list.innerHTML = `<h2>Threads</h2>`;
  const listBody = document.createElement("div");
  list.appendChild(listBody);
  container.appendChild(list);

  const threadIds = extractThreadIds(data);
  const truncated = Boolean(data.truncated);
  const offset = Number(data.offset ?? 0);
  const limit = Number(data.limit ?? 50);
  const total = data.total != null ? Number(data.total) : null;

  const renderRows = (prefix: string) => {
    listBody.innerHTML = "";
    const filtered = prefix
      ? threadIds.filter((id) => id.toLowerCase().startsWith(prefix.toLowerCase()))
      : threadIds;

    if (filtered.length === 0) {
      listBody.innerHTML = `<p class="empty">No threads discovered — check profile or backend limits.</p>`;
      return;
    }

    for (const id of filtered) {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "row";
      row.style.width = "100%";
      row.style.textAlign = "left";
      row.style.color = "inherit";

      const label = document.createElement("span");
      label.className = "row-id";
      label.textContent = id.length > 24 ? `${id.slice(0, 10)}…${id.slice(-8)}` : id;
      label.title = id;
      row.appendChild(label);

      const meta = document.createElement("span");
      meta.className = "meta";
      const updated = threadLastUpdated(data, id);
      meta.textContent = updated ? formatTs(updated) : "→";
      meta.title = updated ?? id;
      row.appendChild(meta);

      row.addEventListener("click", () => onSelect(id));
      listBody.appendChild(row);
    }
  };

  filter.addEventListener("input", () => renderRows(filter.value.trim()));
  renderRows("");

  if (truncated) {
    const banner = document.createElement("div");
    banner.className = "banner warn";
    banner.textContent = "Response truncated — ask the model to load more or use Load more.";
    container.insertBefore(banner, list);
  }

  const pager = document.createElement("div");
  pager.className = "pager";
  const pageLabel = total != null ? `Showing ${offset + 1}–${offset + threadIds.length} of ${total}` : `${threadIds.length} threads`;
  pager.innerHTML = `<span>${pageLabel}</span>`;

  const more = document.createElement("button");
  more.type = "button";
  more.className = "primary";
  more.textContent = "Load more";
  more.disabled = !truncated && threadIds.length < limit;
  more.addEventListener("click", onLoadMore);
  pager.appendChild(more);
  container.appendChild(pager);
}

function formatTs(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}
