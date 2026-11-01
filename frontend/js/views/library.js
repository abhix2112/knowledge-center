// The article list: filters, search results, pagination.

import { api } from "../api.js";
import { navigate } from "../app.js";
import { html, mount, plainText, statusBadge, timeAgo } from "../util.js";

const PAGE_SIZE = 20;

const STATUS_FILTERS = [
  ["", "All"],
  ["published", "Published"],
  ["draft", "Drafts"],
  ["retired", "Retired"],
];

export async function showLibrary(main, { query, alive }) {
  const q = query.get("q") || "";
  const category = query.get("category") || "";
  const status = query.get("status") || "";
  const mine = query.get("mine") === "true";
  const page = Math.max(1, Number(query.get("page")) || 1);

  const params = new URLSearchParams({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  if (status) params.set("status", status);
  if (mine) params.set("mine", "true");

  const list = await api(`/articles?${params}`);
  if (!alive()) return;

  // Link to this page with some filters changed. Changing a filter resets to page 1.
  const link = (changes) => {
    const next = new URLSearchParams(query);
    if (!("page" in changes)) next.delete("page");
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    const qs = next.toString();
    return `#/${qs ? `?${qs}` : ""}`;
  };

  const heading = q ? `Results for “${q}”` : category || "All articles";
  const countText = `${list.total} ${list.total === 1 ? "article" : "articles"}${q && category ? ` in ${category}` : ""}`;
  const first = list.total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const last = Math.min(page * PAGE_SIZE, list.total);

  mount(
    main,
    html`
      <div class="page-head">
        <div>
          <h1>${heading}</h1>
          <p class="sub">${countText}</p>
        </div>
        <div class="actions">
          <a class="button" href="#/upload">Upload document</a>
          <a class="button primary" href="#/new">New article</a>
        </div>
      </div>

      <div class="toolbar">
        <nav class="segmented" aria-label="Filter by status">
          ${STATUS_FILTERS.map(([value, label]) =>
            html`<a href="${link({ status: value })}" aria-current="${status === value ? "page" : "false"}">${label}</a>`)}
        </nav>
        <label class="toggle"><input type="checkbox" data-mine ${mine ? "checked" : ""} /> Only my articles</label>
      </div>

      ${list.items.length
        ? html`<ul class="rows">${list.items.map(articleRow)}</ul>`
        : emptyState({ q, category, status, mine })}

      ${list.total > PAGE_SIZE
        ? html`<div class="pager">
            <span>${first}–${last} of ${list.total}</span>
            <div class="actions">
              ${page > 1 ? html`<a class="button" href="${link({ page: page - 1 })}">Previous</a>` : ""}
              ${last < list.total ? html`<a class="button" href="${link({ page: page + 1 })}">Next</a>` : ""}
            </div>
          </div>`
        : ""}
    `,
  );

  main.querySelector("[data-mine]").addEventListener("change", (event) => {
    navigate(link({ mine: event.target.checked ? "true" : "" }).slice(1));
  });
}

function articleRow(article) {
  return html`
    <li>
      <a class="row ${article.status}" href="#/articles/${article.id}">
        <span class="plate">${article.number}</span>
        <span>
          <span class="row-title">${article.title}</span>
          <span class="row-excerpt">${plainText(article.excerpt)}</span>
        </span>
        <span class="row-meta">
          ${statusBadge(article.status)}
          <span>Updated ${timeAgo(article.updated_at)}</span>
        </span>
      </a>
    </li>`;
}

function emptyState({ q, category, status, mine }) {
  if (q) {
    return html`<div class="empty">
      <h2>No articles match “${q}”</h2>
      <p>Try fewer or different words. You can also search by KB number, like KB0001003.</p>
      <div class="actions"><a class="button" href="#/">Clear search</a></div>
    </div>`;
  }
  if (status || mine || category) {
    return html`<div class="empty">
      <h2>No articles here yet</h2>
      <p>Nothing matches these filters.</p>
      <div class="actions"><a class="button" href="#/">Show all articles</a></div>
    </div>`;
  }
  return html`<div class="empty">
    <h2>The knowledge base is empty</h2>
    <p>Write the first article, or upload a PDF, Word or Markdown document to turn it into a draft.</p>
    <div class="actions">
      <a class="button primary" href="#/new">New article</a>
      <a class="button" href="#/upload">Upload document</a>
    </div>
  </div>`;
}
