import { api, session } from "../api.js";
import { navigate } from "../app.js";
import { html, mount } from "../util.js";

const DEMO_USERS = [
  ["Alice", "alice@halden.example", "IT Service Desk"],
  ["Bob", "bob@halden.example", "Security"],
  ["Priya", "priya@halden.example", "People team"],
];
const DEMO_PASSWORD = "password123";

export function showSignIn(app, mode = "signin") {
  const creating = mode === "register";

  mount(
    app,
    html`
      <div class="signin">
        <section class="signin-intro">
          <span class="brand"><span class="brand-mark" aria-hidden="true">K</span>Knowledge Center</span>
          <div>
            <h1>Answers to the questions Halden staff ask every day.</h1>
            <p>Search the knowledge base, write and publish articles, and turn documents into drafts.</p>
          </div>
          <div class="catalogue" aria-hidden="true">
            <div class="entry"><span class="plate">KB0001001</span>Connect to the corporate VPN</div>
            <div class="entry"><span class="plate">KB0001005</span>Reset your password</div>
            <div class="entry"><span class="plate">KB0001020</span>Spot and report phishing emails</div>
          </div>
        </section>

        <section class="signin-form">
          <h2>${creating ? "Create an account" : "Sign in"}</h2>
          <p class="sub">${creating ? "You'll be signed in right away." : "Use your email and password."}</p>
          <form novalidate>
            ${creating
              ? html`<div><label for="full_name">Full name</label>
                  <input class="input" id="full_name" name="full_name" autocomplete="name" required /></div>`
              : ""}
            <div><label for="email">Email</label>
              <input class="input" id="email" name="email" type="email" autocomplete="email" required /></div>
            <div><label for="password">Password</label>
              <input class="input" id="password" name="password" type="password" required
                autocomplete="${creating ? "new-password" : "current-password"}" />
              ${creating ? html`<p class="hint">At least 8 characters.</p>` : ""}</div>
            <div class="error" hidden></div>
            <button class="button primary" type="submit">${creating ? "Create account" : "Sign in"}</button>
          </form>
          <p class="switch">
            ${creating ? "Already have an account? " : "New here? "}
            <button type="button" data-switch>${creating ? "Sign in" : "Create an account"}</button>
          </p>

          ${creating
            ? ""
            : html`<div class="demo">
                <h3>Try a demo account</h3>
                <p>Each has different articles, including private ones and drafts.</p>
                <div class="actions">
                  ${DEMO_USERS.map(([name, email, team]) =>
                    html`<button class="button" type="button" data-demo="${email}" title="${team}">${name}</button>`)}
                </div>
              </div>`}
        </section>
      </div>
    `,
  );

  const form = app.querySelector("form");
  const errorBox = app.querySelector(".error");

  async function signIn(email, password) {
    const { access_token } = await api("/auth/login", { method: "POST", form: { username: email, password } });
    session.save(access_token);
    navigate("/");
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    const button = form.querySelector("[type=submit]");
    button.disabled = true;
    errorBox.hidden = true;
    try {
      if (creating) {
        await api("/auth/register", { method: "POST", json: data });
      }
      await signIn(data.email, data.password);
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
      button.disabled = false;
    }
  });

  app.querySelector("[data-switch]").addEventListener("click", () =>
    showSignIn(app, creating ? "signin" : "register"),
  );

  app.querySelectorAll("[data-demo]").forEach((button) =>
    button.addEventListener("click", () =>
      signIn(button.dataset.demo, DEMO_PASSWORD).catch((error) => {
        errorBox.textContent = `${error.message}. Load the demo data first: uv run python -m knowledge_center.seed`;
        errorBox.hidden = false;
      }),
    ),
  );
}
