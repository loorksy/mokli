import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import ar from "./locales/ar.json";
import en from "./locales/en.json";

const stored = localStorage.getItem("mokli-lang") || "ar";

void i18n.use(initReactI18next).init({
  resources: { ar: { translation: ar }, en: { translation: en } },
  lng: stored,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export function applyDirection(language: string) {
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  localStorage.setItem("mokli-lang", language);
}

applyDirection(stored);
export default i18n;
