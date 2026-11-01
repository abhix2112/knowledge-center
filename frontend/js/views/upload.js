// Upload a document; the API turns it into a draft article.

import { api } from "../api.js";
import { navigate, refreshCategories, state } from "../app.js";
import { formatBytes, html, mount, timeAgo, toast } from "../util.js";

const ACCEPTED = ".pdf,.docx,.md,.txt";

export async function showUpload(main, { alive }) {
  const documents = await api("/documents");
  if (!alive()) return;

  mount(
    main,
    html`
      <a class="back" href="#/">← All articles</a>
      <div class="page-head">
        <div>
          <h1>Upload a document</h1>
          <p class="sub">The text becomes a draft article you can review and publish.</p>
        </div>
      </div>
      <form class="form" novalidate>
        <label class="dropzone" for="file">
          <strong>Drop a file here, or click to choose one</strong>
          <span class="hint">PDF, Word (.docx), Markdown or text. Up to 10 MB.</span>
          <span class="file" hidden></span>
        </label>
        <input class="visually-hidden" id="file" name="file" type="file" accept="${ACCEPTED}" />
        <div class="form-row">
          <div>
            <label for="category">Category</label>
            <input class="input" id="category" name="category" list="category-list" value="General" maxlength="50" />
            <datalist id="category-list">
              ${state.categories.map((item) => html`<option value="${item.category}"></option>`)}
            </datalist>
          </div>
        </div>
        <div class="error" hidden></div>
        <div class="form-actions">
          <button class="button primary" type="submit" disabled>Create draft</button>
          <a class="button" href="#/">Cancel</a>
        </div>
      </form>

      ${documents.length
        ? html`<section class="uploads">
            <h2>Your uploads</h2>
            <ul class="rows">
              ${documents.map((doc) => html`<li>
                <a class="row" href="${doc.article_id ? `#/articles/${doc.article_id}` : "#/upload"}">
                  <span class="plate">${doc.filename.split(".").pop().toUpperCase()}</span>
                  <span><span class="row-title">${doc.filename}</span>
                    <span class="row-excerpt">${formatBytes(doc.size_bytes)}${doc.article_id ? "" : ", draft deleted"}</span></span>
                  <span class="row-meta"><span>${timeAgo(doc.created_at)}</span></span>
                </a></li>`)}
            </ul>
          </section>`
        : ""}
    `,
  );

  const form = main.querySelector("form");
  const input = form.querySelector("#file");
  const dropzone = form.querySelector(".dropzone");
  const fileLabel = form.querySelector(".file");
  const submit = form.querySelector("[type=submit]");
  const errorBox = form.querySelector(".error");

  function showChosenFile() {
    const file = input.files[0];
    fileLabel.hidden = !file;
    fileLabel.textContent = file ? `${file.name} (${formatBytes(file.size)})` : "";
    submit.disabled = !file;
  }

  input.addEventListener("change", showChosenFile);
  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragging"));
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
    if (event.dataTransfer.files.length) {
      input.files = event.dataTransfer.files;
      showChosenFile();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    submit.textContent = "Creating draft…";
    errorBox.hidden = true;
    try {
      const result = await api("/documents", { method: "POST", body: new FormData(form) });
      toast(`Draft created from ${result.document.filename}`);
      await refreshCategories();
      navigate(`/articles/${result.article.id}`);
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
      submit.disabled = false;
      submit.textContent = "Create draft";
    }
  });
}
