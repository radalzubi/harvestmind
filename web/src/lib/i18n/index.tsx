"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { en } from "./en";
import { ar } from "./ar";

export type Locale = "en" | "ar";
export type Copy = typeof en;
const COPY: Record<Locale, Copy> = { en, ar };
const KEY = "zaad.locale";

type Ctx = { locale: Locale; setLocale: (l: Locale) => void; t: Copy; dir: "ltr" | "rtl" };
const LocaleContext = createContext<Ctx>({ locale: "en", setLocale: () => {}, t: en, dir: "ltr" });

function initial(): Locale {
  if (typeof window === "undefined") return "en";
  try {
    const saved = window.localStorage.getItem(KEY);
    if (saved === "ar" || saved === "en") return saved;
    return navigator.language?.toLowerCase().startsWith("ar") ? "ar" : "en";
  } catch { return "en"; }
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  useEffect(() => { setLocaleState(initial()); }, []);
  useEffect(() => {
    const root = document.documentElement;
    const previousLang = root.lang;
    const previousDir = root.dir;
    root.lang = locale;
    root.dir = locale === "ar" ? "rtl" : "ltr";
    return () => {
      root.lang = previousLang;
      root.dir = previousDir;
    };
  }, [locale]);
  const value = useMemo<Ctx>(() => ({
    locale,
    dir: locale === "ar" ? "rtl" : "ltr",
    t: COPY[locale],
    setLocale: (l) => { setLocaleState(l); try { window.localStorage.setItem(KEY, l); } catch { /* private mode */ } },
  }), [locale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): Ctx { return useContext(LocaleContext); }
