/**
 * Typed API client for Sasha Health.
 *
 * Sends Telegram initData via `Authorization: tma <initData>` header
 * on every request. Falls back gracefully when running outside Telegram
 * (dev mode — mock user, or PWA with stored credentials).
 */

const BASE_URL = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function getInitData(): string {
  if (typeof window === "undefined") return "";

  const tg = (window as any).Telegram?.WebApp;
  if (tg?.initData) return tg.initData;

  // PWA fallback: store initData in sessionStorage after first auth
  const stored = sessionStorage.getItem("tg_init_data");
  return stored ?? "";
}

function authHeaders(): Record<string, string> {
  const initData = getInitData();
  if (initData) return { Authorization: `tma ${initData}` };

  const webAuthRaw = sessionStorage.getItem("web_auth");
  if (webAuthRaw) {
    try {
      const webAuth = JSON.parse(webAuthRaw);
      if (webAuth?.user_id) return { "X-User-ID": String(webAuth.user_id) };
    } catch {
      /* corrupt storage */
    }
  }

  return {};
}

async function handleResponse(res: Response): Promise<unknown> {
  if (res.ok) {
    const text = await res.text();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }

  let body: unknown = null;
  try {
    body = JSON.parse(await res.text());
  } catch {
    /* non-JSON body */
  }

  const message =
    typeof body === "object" && body !== null && "detail" in body
      ? String((body as any).detail)
      : `API ${res.status} on ${res.url}`;

  throw new ApiError(res.status, message, body);
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers as Record<string, string> | undefined),
    },
  });
  return (await handleResponse(res)) as T;
}

/** POST JSON body */
export async function apiPost<T = unknown>(
  path: string,
  body?: unknown,
  options: RequestInit = {},
): Promise<T> {
  return apiFetch<T>(path, {
    ...options,
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/** PUT JSON body */
export async function apiPut<T = unknown>(
  path: string,
  body?: unknown,
  options: RequestInit = {},
): Promise<T> {
  return apiFetch<T>(path, {
    ...options,
    method: "PUT",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/** DELETE request */
export async function apiDelete<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  return apiFetch<T>(path, {
    ...options,
    method: "DELETE",
  });
}
