// Small wrapper around fetch for the /api endpoints.

const TOKEN_KEY = "knowledge-center.token";

export const session = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  save(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
};

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

/**
 * Call the API. Pass `json` for JSON bodies, `form` for URL-encoded forms
 * (login), or `body` for FormData (file upload).
 */
export async function api(path, { method = "GET", json, form, body } = {}) {
  const headers = {};
  if (session.token) headers.Authorization = `Bearer ${session.token}`;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form !== undefined) {
    body = new URLSearchParams(form);
  }

  let response;
  try {
    response = await fetch(`/api${path}`, { method, headers, body });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check that the API is running.");
  }

  if (response.status === 401 && path !== "/auth/login") {
    session.clear();
    location.hash = "#/login";
    throw new ApiError(401, "Your session expired. Sign in again.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  return response.status === 204 ? null : response.json();
}

// FastAPI errors look like {"detail": "message"} or, for validation errors,
// {"detail": [{"loc": ["body", "password"], "msg": "..."}]}.
async function errorMessage(response) {
  try {
    const { detail } = await response.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((error) => {
          const field = error.loc.filter((part) => part !== "body").join(" ");
          return field ? `${field}: ${error.msg}` : error.msg;
        })
        .join(". ");
    }
  } catch {
    // not JSON
  }
  return `Request failed (${response.status})`;
}
