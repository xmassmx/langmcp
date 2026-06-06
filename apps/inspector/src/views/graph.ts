import { card, elem } from "../components.js";

type CpNode = {
  id: string;
  step: string | null;
  source: string | null;
  endpoint: string | null;
  timestamp: string;
  requestId: string | null;
};

type CpEdge = { from: string; to: string; lane: string };

function checkpointId(item: Record<string, unknown>): string {
  return String(item.checkpoint_id ?? item.id ?? item.checkpoint ?? "");
}

function shortId(id: string): string {
  return id.length > 14 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}

function metadata(item: Record<string, unknown>): Record<string, unknown> {
  return (item.metadata as Record<string, unknown> | undefined) ?? {};
}

function nodeFromItem(item: Record<string, unknown>): CpNode {
  const meta = metadata(item);
  return {
    id: checkpointId(item),
    step: meta.step != null ? String(meta.step) : null,
    source: meta.source != null ? String(meta.source) : null,
    endpoint: meta.endpoint != null ? String(meta.endpoint) : null,
    timestamp: String(item.timestamp ?? ""),
    requestId: meta.request_id != null ? String(meta.request_id) : null,
  };
}

function parentEdges(item: Record<string, unknown>): CpEdge[] {
  const to = checkpointId(item);
  const parents = metadata(item).parents;
  if (!parents || typeof parents !== "object") return [];
  return Object.entries(parents as Record<string, unknown>).map(([lane, value]) => ({
    from: String(value),
    to,
    lane: lane || "default",
  }));
}

function nodeLabel(node: CpNode | undefined, id: string): string {
  if (!node) return shortId(id);
  const parts = [
    node.step != null ? `step ${node.step}` : null,
    node.source,
  ].filter(Boolean);
  return parts.length ? `${parts.join(" · ")} (${shortId(id)})` : shortId(id);
}

function buildModel(items: Record<string, unknown>[]) {
  const nodes = new Map<string, CpNode>();
  for (const item of items) {
    const id = checkpointId(item);
    if (id) nodes.set(id, nodeFromItem(item));
  }

  const edgeMap = new Map<string, CpEdge>();
  for (const item of items) {
    for (const edge of parentEdges(item)) {
      if (!edge.from || !edge.to) continue;
      if (!nodes.has(edge.from)) {
        nodes.set(edge.from, {
          id: edge.from,
          step: null,
          source: null,
          endpoint: null,
          timestamp: "",
          requestId: null,
        });
      }
      edgeMap.set(`${edge.from}|${edge.to}|${edge.lane}`, edge);
    }
  }

  const edges = [...edgeMap.values()];
  const childCount = new Map<string, number>();
  for (const edge of edges) {
    childCount.set(edge.from, (childCount.get(edge.from) ?? 0) + 1);
  }

  const latest = [...nodes.values()]
    .filter((n) => n.timestamp)
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))[0];

  const stepCounts = new Map<string, number>();
  const sourceCounts = new Map<string, number>();
  for (const node of nodes.values()) {
    if (!node.id || node.step == null) continue;
    stepCounts.set(node.step, (stepCounts.get(node.step) ?? 0) + 1);
    if (node.source) sourceCounts.set(node.source, (sourceCounts.get(node.source) ?? 0) + 1);
  }

  const requestIds = new Set(
    [...nodes.values()].map((n) => n.requestId).filter((id): id is string => Boolean(id)),
  );

  return { nodes, edges, childCount, latest, stepCounts, sourceCounts, requestIds };
}

function renderSummary(parent: HTMLElement, items: Record<string, unknown>[], model: ReturnType<typeof buildModel>): void {
  const section = card("What happened");
  const grid = elem("div", "graph-stats");

  const steps = [...model.stepCounts.keys()]
    .map((s) => Number(s))
    .filter((n) => !Number.isNaN(n))
    .sort((a, b) => a - b);
  const stepRange = steps.length ? `${steps[0]} → ${steps[steps.length - 1]}` : "—";

  const topSource = [...model.sourceCounts.entries()].sort((a, b) => b[1] - a[1])[0];
  const forks = [...model.childCount.values()].filter((c) => c > 1).length;

  const addStat = (label: string, value: string) => {
    const box = elem("div", "graph-stat");
    box.append(elem("span", "graph-stat-label", label), elem("span", "graph-stat-value", value));
    grid.appendChild(box);
  };

  addStat("Checkpoints", String(items.length));
  addStat("Steps", stepRange);
  addStat("Fork points", String(forks));
  addStat("Parent links", String(model.edges.length));
  if (topSource) addStat("Mostly", `${topSource[0]} (${topSource[1]}×)`);
  if (model.requestIds.size === 1) {
    const req = [...model.requestIds][0]!;
    addStat("Request", shortId(req));
  }

  section.appendChild(grid);

  if (model.latest) {
    const latest = elem("p", "graph-latest");
    latest.textContent = `Latest: ${nodeLabel(model.latest, model.latest.id)}`;
    section.appendChild(latest);
  }

  if (model.stepCounts.size > 0) {
    const hist = elem("div", "graph-histogram");
    const max = Math.max(...model.stepCounts.values());
    for (const [step, count] of [...model.stepCounts.entries()].sort(
      (a, b) => Number(a[0]) - Number(b[0]),
    )) {
      const row = elem("div", "graph-bar-row");
      row.append(elem("span", "graph-bar-label", `step ${step}`));
      const track = elem("div", "graph-bar-track");
      const fill = elem("div", "graph-bar-fill");
      fill.style.width = `${Math.max(12, Math.round((count / max) * 100))}%`;
      fill.textContent = String(count);
      track.appendChild(fill);
      row.appendChild(track);
      hist.appendChild(row);
    }
    section.appendChild(elem("p", "graph-hint", "Bar height = how many checkpoints were saved at each step (loops create repeats)."));
    section.appendChild(hist);
  }

  parent.appendChild(section);
}

function renderBranches(parent: HTMLElement, model: ReturnType<typeof buildModel>): void {
  if (model.edges.length === 0) return;

  const section = card("Parent links");
  const list = elem("div", "graph-edges");
  const sorted = [...model.edges].sort((a, b) => a.from.localeCompare(b.from));
  for (const edge of sorted.slice(0, 12)) {
    const row = elem("div", "graph-edge-row");
    const from = model.nodes.get(edge.from);
    const to = model.nodes.get(edge.to);
    row.append(
      elem("span", "graph-edge-from", nodeLabel(from, edge.from)),
      elem("span", "graph-edge-arrow", "→"),
      elem("span", "graph-edge-to", nodeLabel(to, edge.to)),
    );
    if (edge.lane !== "default") {
      row.appendChild(elem("span", "graph-edge-lane", edge.lane));
    }
    list.appendChild(row);
  }
  if (sorted.length > 12) {
    list.appendChild(elem("p", "graph-hint", `Showing 12 of ${sorted.length} links. Open Checkpoints for the full list.`));
  }
  section.appendChild(list);
  parent.appendChild(section);
}

function layoutNodes(nodeIds: string[], edges: CpEdge[]): Map<string, { x: number; y: number }> {
  const depth = new Map<string, number>();
  const assignDepth = (id: string, d: number) => {
    depth.set(id, Math.max(depth.get(id) ?? 0, d));
    for (const edge of edges) {
      if (edge.from === id) assignDepth(edge.to, d + 1);
    }
  };
  const targets = new Set(edges.map((e) => e.to));
  const roots = nodeIds.filter((id) => !targets.has(id));
  for (const root of roots.length ? roots : nodeIds.slice(0, 1)) assignDepth(root, 0);
  for (const id of nodeIds) if (!depth.has(id)) depth.set(id, 0);

  const layers = new Map<number, string[]>();
  for (const id of nodeIds) {
    const d = depth.get(id) ?? 0;
    const layer = layers.get(d) ?? [];
    layer.push(id);
    layers.set(d, layer);
  }

  const positions = new Map<string, { x: number; y: number }>();
  const colW = 118;
  const rowH = 34;
  for (const [d, layer] of layers) {
    layer.forEach((id, index) => {
      positions.set(id, { x: 12 + d * colW, y: 12 + index * rowH });
    });
  }
  return positions;
}

function renderSvg(parent: HTMLElement, model: ReturnType<typeof buildModel>): void {
  const nodeIds = [...model.nodes.keys()];
  if (model.edges.length === 0 || nodeIds.length > 14) return;

  const positions = layoutNodes(nodeIds, model.edges);
  const maxX = Math.max(...[...positions.values()].map((p) => p.x)) + 96;
  const maxY = Math.max(...[...positions.values()].map((p) => p.y)) + 28;

  const section = card("Branch map");
  const wrap = elem("div", "graph-svg-wrap");
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "graph-svg");
  svg.setAttribute("viewBox", `0 0 ${maxX} ${maxY}`);
  svg.setAttribute("aria-label", "Checkpoint parent branch map");

  for (const edge of model.edges) {
    const from = positions.get(edge.from);
    const to = positions.get(edge.to);
    if (!from || !to) continue;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", String(from.x + 44));
    line.setAttribute("y1", String(from.y + 10));
    line.setAttribute("x2", String(to.x + 4));
    line.setAttribute("y2", String(to.y + 10));
    line.setAttribute("class", "graph-svg-edge");
    svg.appendChild(line);
  }

  for (const id of nodeIds) {
    const pos = positions.get(id);
    const node = model.nodes.get(id);
    if (!pos || !node) continue;
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("transform", `translate(${pos.x} ${pos.y})`);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("width", "88");
    rect.setAttribute("height", "20");
    rect.setAttribute("rx", "6");
    rect.setAttribute("class", "graph-svg-node");
    if (model.latest?.id === id) rect.setAttribute("class", "graph-svg-node graph-svg-node-latest");
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", "6");
    text.setAttribute("y", "13");
    text.textContent = node.step != null ? `s${node.step}` : shortId(id);
    g.append(rect, text);
    svg.appendChild(g);
  }

  wrap.appendChild(svg);
  section.appendChild(wrap);
  section.appendChild(
    elem("p", "graph-hint", "Arrows follow parent checkpoint links from metadata, not chronological order."),
  );
  parent.appendChild(section);
}

export function renderGraphView(container: HTMLElement, items: Record<string, unknown>[]): void {
  if (items.length === 0) {
    const empty = card("Graph");
    empty.appendChild(elem("p", "empty", "No checkpoints available."));
    container.appendChild(empty);
    return;
  }

  const model = buildModel(items);
  renderSummary(container, items, model);
  renderBranches(container, model);
  renderSvg(container, model);

  if (model.edges.length === 0 && model.stepCounts.size <= 1) {
    const note = card("Graph");
    note.appendChild(
      elem(
        "p",
        "empty",
        "Only a single step shape in history — use Checkpoints for IDs or State for channel values.",
      ),
    );
    container.appendChild(note);
  }
}
