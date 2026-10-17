"use client";

// Minimal two-language (en/fa) i18n, hand-rolled to keep the dependency-free
// posture of this app.  The chosen language drives three things: the strings
// (in ./i18n/strings.js), the `lang` query param sent to the wizard API (which
// resolves per-language content columns server-side), and <html dir> — Persian
// is RTL.
//
// Only the wizard surface is translated; the older chat screens stay English.
//
// Two modes:
//   <LangProvider lang="fa">  public pages — the language comes from the URL
//                             (/fa/...), is server-rendered, and is remembered
//                             as the visitor's preference for the app.
//   <LangProvider>            app pages — the language is the stored
//                             preference, read after mount so the first client
//                             render matches the server's.

import { createContext, createElement, useContext, useEffect, useMemo, useState } from "react";
import { DEFAULT_LANG, LANGS, STORAGE_KEY, isRtl, translate } from "./i18n/strings.js";

export { DEFAULT_LANG, LANGS, isRtl, localePath, translate } from "./i18n/strings.js";

function readStoredLang() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (LANGS.includes(stored)) return stored;
  } catch {
    /* private mode / storage disabled */
  }
  return DEFAULT_LANG;
}

export function storeLang(lang) {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* ignore */
  }
}

const LangContext = createContext(null);

export function LangProvider({ lang: fixedLang, children }) {
  const [lang, setLangState] = useState(fixedLang || DEFAULT_LANG);

  useEffect(() => {
    if (fixedLang) {
      storeLang(fixedLang);
      setLangState(fixedLang);
    } else {
      setLangState(readStoredLang());
    }
  }, [fixedLang]);

  // The document direction is global state that lives outside React, so it is
  // set here rather than in whichever component happens to render first.  The
  // public pages already ship the right <html lang/dir> from the server.
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = isRtl(lang) ? "rtl" : "ltr";
  }, [lang]);

  const value = useMemo(
    () => ({
      lang,
      rtl: isRtl(lang),
      setLang: (next) => {
        if (!LANGS.includes(next)) return;
        storeLang(next);
        setLangState(next);
      },
      t: (key, vars) => translate(lang, key, vars),
    }),
    [lang]
  );

  return createElement(LangContext.Provider, { value }, children);
}

export function useT() {
  const ctx = useContext(LangContext);
  if (!ctx) {
    // Lets components render outside the provider (e.g. in isolation) without
    // crashing; they just get untranslated English.
    return {
      lang: DEFAULT_LANG,
      rtl: false,
      setLang: () => {},
      t: (key, vars) => translate(DEFAULT_LANG, key, vars),
    };
  }
  return ctx;
}
