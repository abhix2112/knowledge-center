// One article: content, details, lifecycle actions, version history.

import { api } from "../api.js";
import { navigate, refreshCategories, render, state } from "../app.js";
import { formatDate, html, mount, renderMarkdown, statusBadge, timeAgo, toast } from "../util.js";

const SOURCE_LABELS = { manual: "Written here", upload: "Uploaded document", seed: "Demo data" };

// What each lifecycle button does, and the message shown afterwards.
const ACTIONS = {
  publish: { label: "Publish", done: "Published", primary: true },
  retire: { label: "Retire", done: "Retired" },
  restore: { label: "Restore as draft", done: "Restored as a draft" },
};
const ACTIONS_BY_STATUS = { draft: ["publish"], published: ["retire"], retired: ["restore"] };

export async function showArticle(main, { params: [id], query, alive }) {
  // Independent requests, so fetch them at the same time (like asyncio.gather).
  const [article, versions] = await Promise.all([api(`/articles/${id}`), api(`/articles/${id}/versions`)]);

  const requested = Number(query.get("version"));
  const viewingOld = requested && requested !== article.current_version;
  const shown = viewingOld ? await api(`/articles/${id}/versions/${requested}`) : article;
  if (!alive()) return;

  const isOwner = article.owner_id === state.user.id;

  mount(
    main,
    html`
      <a class="back" href="#/">← All articles</a>
      <div class="article-layout">
        <article>
          <header class="article-head">
            <span class="plate">${article.number}</span>
            <h1>${shown.title}</h1>
            <div class="byline">
              ${statusBadge(article.status)}
              <span>By ${article.owner_name}</span>
              <span>Updated ${timeAgo(article.updated_at)}</span>
            </div>
          </header>
          ${banner(article, viewingOld ? shown : null, isOwner)}
          <div class="prose">${renderMarkdown(shown.body)}</div>
        </article>

        <aside class="aside">
          ${isOwner ? ownerActions(article) : ""}
          <section>
            <h2>Details</h2>
            <dl class="details">
              <dt>Category</dt>
              <dd><a href="#/?category=${encodeURIComponent(article.category)}">${article.category}</a></dd>
              <dt>Owner</dt><dd>${article.owner_name}</dd>
              <dt>Visible to</dt><dd>${article.visibility === "public" ? "Everyone, once published" : "Only the owner"}</dd>
              <dt>Version</dt><dd>${article.current_version}</dd>
              <dt>Source</dt><dd>${SOURCE_LABELS[article.source] ?? article.source}</dd>
              ${article.published_at ? html`<dt>Published</dt><dd>${formatDate(article.published_at)}</dd>` : ""}
              <dt>Created</dt><dd>${formatDate(article.created_at)}</dd>
            </dl>
          </section>
          ${article.tags.length
            ? html`<section><h2>Tags</h2><div class="tags">${article.tags.map((tag) => html`<span class="tag">${tag}</span>`)}</div></section>`
            : ""}
          <section>
            <h2>Version history</h2>
            <ol class="versions">
              ${versions.map((version) => {
                const isCurrent = version.version === article.current_version;
                const isShown = version.version === shown.version || (!viewingOld && isCurrent);
                const href = isCurrent ? `#/articles/${id}` : `#/articles/${id}?version=${version.version}`;
                return html`<li>
                  <a href="${href}" aria-current="${isShown ? "true" : "false"}">
                    <span class="v">v${version.version}</span>
                    <span>${isCurrent ? "Current" : version.title}</span>
                    <span class="when">${version.created_by_name}, ${timeAgo(version.created_at)}</span>
                  </a></li>`;
              })}
            </ol>
          </section>
        </aside>
      </div>
    `,
  );

  main.querySelectorAll("[data-action]").forEach((button) =>
    button.addEventListener("click", () => runAction(article, button.dataset.action)),
  );
  main.querySelector("[data-delete]")?.addEventListener("click", () => deleteDraft(article));
}

function banner(article, oldVersion, isOwner) {
  if (oldVersion) {
    return html`<div class="banner">
      <span>You're viewing version ${oldVersion.version} from ${formatDate(oldVersion.created_at)}. The current version is ${article.current_version}.</span>
      <a class="button" href="#/articles/${article.id}">View current version</a></div>`;
  }
  if (article.status === "draft" && isOwner) {
    return html`<div class="banner">Draft. Only you can see it until you publish it.</div>`;
  }
  if (article.status === "retired") {
    return html`<div class="banner retired">Retired. Only you can see it. Restore it to edit and publish it again.</div>`;
  }
  return "";
}

function ownerActions(article) {
  return html`<section>
    <h2>Actions</h2>
    <div class="actions">
      ${article.status !== "retired" ? html`<a class="button" href="#/articles/${article.id}/edit">Edit</a>` : ""}
      ${ACTIONS_BY_STATUS[article.status].map((action) =>
        html`<button class="button ${ACTIONS[action].primary ? "primary" : ""}" type="button" data-action="${action}">${ACTIONS[action].label}</button>`)}
      ${article.status === "draft" ? html`<button class="button danger" type="button" data-delete>Delete draft</button>` : ""}
    </div>
  </section>`;
}

async function runAction(article, action) {
  try {
    await api(`/articles/${article.id}/${action}`, { method: "POST" });
    toast(ACTIONS[action].done);
    await refreshCategories();
    render();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteDraft(article) {
  if (!confirm(`Delete “${article.title}”? This can't be undone.`)) return;
  try {
    await api(`/articles/${article.id}`, { method: "DELETE" });
    toast("Draft deleted");
    await refreshCategories();
    navigate("/");
  } catch (error) {
    toast(error.message, "error");
  }
}
