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

let toastTimer: number | undefined;

export function showToast(message: string): void {
  let toast = document.getElementById("inspector-toast");
  if (!toast) {
    toast = elem("div", "toast");
    toast.id = "inspector-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.dataset.visible = "true";
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    delete toast!.dataset.visible;
  }, 1600);
}

async function copyText(value: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      /* fall through */
    }
  }

  const area = document.createElement("textarea");
  area.value = value;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  area.remove();
  return ok;
}

export function copyButton(value: string): HTMLButtonElement {
  const button = elem("button", "ghost", "Copy");
  button.type = "button";
  button.addEventListener("click", async () => {
    const ok = await copyText(value);
    if (ok) {
      button.textContent = "Copied";
      showToast("Copied to clipboard");
      window.setTimeout(() => {
        button.textContent = "Copy";
      }, 1200);
      return;
    }
    button.textContent = "Select";
    showToast("Clipboard blocked — select and copy manually");
    window.setTimeout(() => {
      button.textContent = "Copy";
    }, 1600);
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
