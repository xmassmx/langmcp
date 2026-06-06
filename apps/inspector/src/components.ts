export function clear(el: HTMLElement): void {
  el.replaceChildren();
}

export function elem<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

export function card(title: string): HTMLElement {
  const section = elem("section", "card");
  section.appendChild(elem("h2", undefined, title));
  return section;
}

export function banner(kind: "warn" | "err", message: string): HTMLElement {
  return elem("div", `banner ${kind}`, message);
}

export function copyButton(value: string): HTMLButtonElement {
  const button = elem("button", "ghost", "Copy");
  button.type = "button";
  button.addEventListener("click", async () => {
    await navigator.clipboard?.writeText(value);
    button.textContent = "Copied";
    window.setTimeout(() => {
      button.textContent = "Copy";
    }, 1200);
  });
  return button;
}

export function jsonTree(value: unknown): HTMLElement {
  const pre = elem("pre", "json-tree");
  pre.textContent = JSON.stringify(value, null, 2);
  return pre;
}

export function field(label: string, value: unknown): HTMLElement {
  const row = elem("div", "field");
  row.append(elem("span", "field-label", label), elem("span", "field-value", String(value ?? "—")));
  return row;
}
