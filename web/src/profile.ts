const nameKey = "mokli-name";

export function displayName() {
  return localStorage.getItem(nameKey) || "Ahmed";
}

export function setDisplayName(name: string) {
  localStorage.setItem(nameKey, name.trim() || "Ahmed");
  window.dispatchEvent(new Event("mokli-profile"));
}

export function flag(key: string, fallback: boolean) {
  const value = localStorage.getItem(key);
  if (value === null) return fallback;
  return value === "1";
}

export function setFlag(key: string, on: boolean) {
  localStorage.setItem(key, on ? "1" : "0");
}
