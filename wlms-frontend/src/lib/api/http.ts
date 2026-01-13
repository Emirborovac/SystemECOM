import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth/tokens";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function refreshTokens(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh })
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data = (await res.json()) as { access_token: string; refresh_token: string };
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

export async function api<T>(
  path: string,
  opts: { method?: HttpMethod; body?: unknown; auth?: boolean } = {}
): Promise<T> {
  const method = opts.method ?? "GET";
  const auth = opts.auth ?? true;

  const isForm = typeof FormData !== "undefined" && opts.body instanceof FormData;
  const headers: Record<string, string> = isForm ? {} : { "Content-Type": "application/json" };
  if (auth) {
    const access = getAccessToken();
    if (access) headers.Authorization = `Bearer ${access}`;
  }

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    method,
    headers,
    body:
      opts.body === undefined
        ? undefined
        : isForm
          ? (opts.body as FormData)
          : JSON.stringify(opts.body)
  });

  if (res.status === 401 && auth) {
    const newAccess = await refreshTokens();
    if (!newAccess) throw new Error("Unauthorized");
    const retry = await fetch(url, {
      method,
      headers: { ...headers, Authorization: `Bearer ${newAccess}` },
      body:
        opts.body === undefined
          ? undefined
          : isForm
            ? (opts.body as FormData)
            : JSON.stringify(opts.body)
    });
    if (!retry.ok) {
      let msg = await retry.text();
      try {
        const parsed = JSON.parse(msg) as any;
        msg = parsed?.detail || parsed?.message || msg;
      } catch {}
      throw new Error(msg);
    }
    return (await retry.json()) as T;
  }

  if (!res.ok) {
    let msg = await res.text();
    try {
      const parsed = JSON.parse(msg) as any;
      msg = parsed?.detail || parsed?.message || msg;
    } catch {}
    throw new Error(msg);
  }
  return (await res.json()) as T;
}

export function apiBaseUrl(): string {
  return API_BASE_URL;
}


