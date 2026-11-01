// Entry point: a tiny hash router (#/, #/articles/<id>, ...) plus the app shell.

import { api, session } from "./api.js";
import { html, mount } from "./util.js";
import { showSignIn } from "./views/signin.js";
import { showLibrary } from "./views/library.js";
import { showArticle } from "./views/article.js";
import { showEditor } from "./views/editor.js";
import { showUpload } from "./views/upload.js";

export const state = {
  user: null,
  categories: [],
};

const routes = [
  [/^\/$/, showLibrary],
  [/^\/new$/, showEditor],
  [/^\/upload$/, showUpload],
  [/^\/articles\/([\w-]+)$/, showArticle],
  [/^\/articles\/([\w-]+)\/edit$/, showEditor],
];

export function navigate(path) {
  location.hash = `#${path}`;
}

export async function refreshCategories() {
  state.categories = await api("/categories");
}

export function signOut() {
  session.clear();
  state.user = null;
  navigate("/login");
}

let currentRoute = 0;

export async function render() {
  const routeId = ++currentRoute;
  const app = document.getElementById("app");
  const [path, queryString = ""] = (location.hash.slice(1) || "/").split("?");
  const query = new URLSearchParams(queryString);

  if (!session.token) {
    if (path !== "/login") return navigate("/login");
    return showSignIn(app);
  }
  if (path === "/login") return navigate("/");

  try {
    if (!state.user) {
      [state.user] = await Promise.all([api("/auth/me"), refreshCategories()]);
    }
  } catch {
    return; // api() already redirected to sign in
  }

  const main = renderShell(app, query, path);
  const context = {
    query,
    alive: () => routeId === currentRoute, // false if the user navigated away meanwhile
  };

  for (const [pattern, view] of routes) {
    const match = path.match(pattern);
    if (match) {
      context.params = match.slice(1);
      try {
        await view(main, context);
      } catch (error) {
        if (context.alive()) {
          mount(main, html`<div class="empty"><h2>Couldn't load this page</h2><p>${error.message}</p>
            <div class="actions"><a class="button" href="#/">Go to all articles</a></div></div>`);
        }
      }
      return;
    }
  }
  mount(main, html`<div class="empty"><h2>Page not found</h2>
    <div class="actions"><a class="button" href="#/">Go to all articles</a></div></div>`);
}

// ---------- Shell: top bar, category tabs, main area ----------

function renderShell(app, query, path) {
  if (!app.querySelector(".layout")) {
    mount(
      app,
      html`
        <header class="topbar">
          <a class="brand" href="#/"><span class="brand-mark" aria-hidden="true">K</span>Knowledge Center</a>
          <form class="search" role="search">
            <label class="visually-hidden" for="search">Search articles</label>
            <input class="input" id="search" name="q" type="search" autocomplete="off"
              placeholder="Search articles, error codes or KB numbers" />
          </form>
          <div class="user">
            <span>Signed in as <strong>${state.user.full_name}</strong></span>
            <button class="button quiet" type="button" data-sign-out>Sign out</button>
          </div>
        </header>
        <div class="layout">
          <nav class="rail" aria-label="Categories"></nav>
          <main class="main" id="main"></main>
        </div>
      `,
    );
    app.querySelector(".search").addEventListener("submit", (event) => {
      event.preventDefault();
      const q = event.target.q.value.trim();
      navigate(q ? `/?q=${encodeURIComponent(q)}` : "/");
    });
    app.querySelector("[data-sign-out]").addEventListener("click", signOut);
  }

  app.querySelector("#search").value = path === "/" ? query.get("q") || "" : "";
  renderRail(app.querySelector(".rail"), path === "/" ? query.get("category") : undefined);
  return app.querySelector("#main");
}

function renderRail(rail, activeCategory) {
  const total = state.categories.reduce((sum, item) => sum + item.count, 0);
  const tab = (label, count, href, active) => html`
    <li><a class="tab" href="${href}" aria-current="${active ? "page" : "false"}">
      <span>${label}</span><span class="count">${count}</span></a></li>`;

  mount(
    rail,
    html`
      <h2>Categories</h2>
      <ul class="tabs">
        ${tab("All articles", total, "#/", activeCategory === null)}
        ${state.categories.map((item) =>
          tab(item.category, item.count, `#/?category=${encodeURIComponent(item.category)}`,
            activeCategory === item.category),
        )}
      </ul>
    `,
  );
}

window.addEventListener("hashchange", () => {
  window.scrollTo(0, 0); // a new page starts at the top
  render();
});
render();
