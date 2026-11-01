import { marked } from "../vendor/marked.esm.js";
import DOMPurify from "../vendor/purify.es.mjs";

// ---------- Safe HTML templates ----------
// html`<p>${userText}</p>` escapes every value, so article content can never
// inject <script> tags. Wrap trusted HTML in raw() to insert it as-is.

class Raw {
  constructor(value) {
    this.value = value;
  }
}

export const raw = (value) => new Raw(value);

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ESCAPES[char]);
}

function toHtml(value) {
  if (value instanceof Raw) return value.value;
  if (Array.isArray(value)) return value.map(toHtml).join("");
  if (value === null || value === undefined || value === false) return "";
  return escapeHtml(value);
}

export function html(strings, ...values) {
  let out = strings[0];
  values.forEach((value, i) => {
    out += toHtml(value) + strings[i + 1];
  });
  return raw(out);
}

export function mount(element, template) {
  element.innerHTML = template.value;
}

// ---------- Markdown ----------

export function renderMarkdown(markdown) {
  return raw(DOMPurify.sanitize(marked.parse(markdown)));
}

/** Markdown without the symbols, for one-line excerpts. */
export function plainText(markdown) {
  return markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/[#>*_`|]/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/-{3,}/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// ---------- Dates ----------

const dateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function formatDate(iso) {
  return iso ? dateFormat.format(new Date(iso)) : "";
}

export function timeAgo(iso) {
  const seconds = (new Date(iso) - Date.now()) / 1000;
  const units = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// ---------- Toasts ----------

export function toast(message, kind = "info") {
  const element = document.createElement("div");
  element.className = `toast ${kind === "error" ? "error" : ""}`;
  element.textContent = message;
  document.getElementById("toasts").append(element);
  setTimeout(() => element.remove(), kind === "error" ? 6000 : 3500);
}

export const STATUS_LABELS = { draft: "Draft", published: "Published", retired: "Retired" };

export function statusBadge(status) {
  return html`<span class="status ${status}">${STATUS_LABELS[status]}</span>`;
}
