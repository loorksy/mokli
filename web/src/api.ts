const tokenKey = "mokli-token";

export function token() {
  return localStorage.getItem(tokenKey) || "";
}

export function setToken(value: string) {
  localStorage.setItem(tokenKey, value);
}

export function clearToken() {
  localStorage.removeItem(tokenKey);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token()) headers.set("Authorization", `Bearer ${token()}`);
  const response = await fetch(path, { ...init, headers });
  if (response.status === 401) {
    clearToken();
    throw new Error("auth");
  }
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}
