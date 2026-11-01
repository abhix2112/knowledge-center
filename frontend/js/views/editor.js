// Create a new article (#/new) or edit an existing one (#/articles/<id>/edit).

import { api } from "../api.js";
import { navigate, refreshCategories, state } from "../app.js";
import { html, mount, renderMarkdown, toast } from "../util.js";

export async function showEditor(main, { params: [id], alive }) {
  const article = id ? await api(`/articles/${id}`) : null;
  if (!alive()) return;

  if (article && (article.owner_id !== state.user.id || article.status === "retired")) {
    const reason = article.status === "retired"
      ? "Retired articles can't be edited. Restore it as a draft first."
      : "Only the owner can edit this article.";
    mount(main, html`<div class="empty"><h2>You can't edit this article</h2><p>${reason}</p>
      <div class="actions"><a class="button" href="#/articles/${article.id}">Back to the article</a></div></div>`);
    return;
  }

  const cancelHref = article ? `#/articles/${article.id}` : "#/";

  mount(
    main,
    html`
      <a class="back" href="${cancelHref}">← ${article ? "Back to the article" : "All articles"}</a>
      <div class="page-head">
        <h1>${article ? "Edit article" : "New article"}</h1>
      </div>
      <form class="form" novalidate>
        <div>
          <label for="title">Title</label>
          <input class="input title-input" id="title" name="title" maxlength="200" required
            value="${article?.title ?? ""}" placeholder="What question does this article answer?" />
        </div>
        <div class="form-row">
          <div>
            <label for="category">Category</label>
            <input class="input" id="category" name="category" list="category-list" maxlength="50"
              value="${article?.category ?? "General"}" />
            <datalist id="category-list">
              ${state.categories.map((item) => html`<option value="${item.category}"></option>`)}
            </datalist>
          </div>
          <div>
            <label for="visibility">Visible to</label>
            <select class="select" id="visibility" name="visibility">
              <option value="public" ${article?.visibility !== "private" ? "selected" : ""}>Everyone, once published</option>
              <option value="private" ${article?.visibility === "private" ? "selected" : ""}>Only me</option>
            </select>
          </div>
          <div>
            <label for="tags">Tags</label>
            <input class="input" id="tags" name="tags" value="${article?.tags.join(", ") ?? ""}"
              placeholder="vpn, remote work" />
          </div>
        </div>
        <div>
          <div class="editor-tabs" role="tablist">
            <button class="button quiet" type="button" role="tab" aria-selected="true" data-tab="write">Write</button>
            <button class="button quiet" type="button" role="tab" aria-selected="false" data-tab="preview">Preview</button>
          </div>
          <label class="visually-hidden" for="body">Article text (Markdown)</label>
          <textarea class="textarea" id="body" name="body" required
            placeholder="Write in Markdown. Use ## for section headings and - for lists.">${article?.body ?? ""}</textarea>
          <div class="preview prose" hidden></div>
          <p class="hint">Markdown supported: ## headings, **bold**, - lists, | tables |, \`code\`.</p>
        </div>
        <div class="error" hidden></div>
        <div class="form-actions">
          <button class="button primary" type="submit">${article ? "Save changes" : "Save draft"}</button>
          <a class="button" href="${cancelHref}">Cancel</a>
          <p class="hint">${article?.status === "published" ? "Saving creates a new version. The article stays published." : "Ctrl+S saves"}</p>
        </div>
      </form>
    `,
  );

  const form = main.querySelector("form");
  const textarea = form.querySelector("#body");
  const preview = form.querySelector(".preview");
  const errorBox = form.querySelector(".error");

  // Write / Preview tabs
  form.querySelectorAll("[data-tab]").forEach((tab) =>
    tab.addEventListener("click", () => {
      const showPreview = tab.dataset.tab === "preview";
      if (showPreview) preview.innerHTML = renderMarkdown(textarea.value || "*Nothing to preview yet.*").value;
      preview.hidden = !showPreview;
      textarea.hidden = showPreview;
      form.querySelectorAll("[data-tab]").forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
    }),
  );

  form.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "s") {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    const payload = {
      title: data.title,
      body: data.body,
      category: data.category || "General",
      visibility: data.visibility,
      tags: data.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
    };
    const button = form.querySelector("[type=submit]");
    button.disabled = true;
    errorBox.hidden = true;
    try {
      const saved = article
        ? await api(`/articles/${article.id}`, { method: "PATCH", json: payload })
        : await api("/articles", { method: "POST", json: payload });
      toast(article ? "Changes saved" : "Draft saved");
      await refreshCategories();
      navigate(`/articles/${saved.id}`);
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
      button.disabled = false;
    }
  });

  form.querySelector("#title").focus();
}
