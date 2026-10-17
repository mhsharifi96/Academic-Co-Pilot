"use client";

import { useT } from "../i18n.js";

// EN / فارسی segmented control.
//
// On the public pages each language has its own URL, so pass `hrefs`
// ({en, fa}) and the options become links (a full navigation — the two
// languages are separate root layouts with their own <html lang/dir>).
// Inside the app there is no locale in the URL; switching flips <html dir>
// (handled in LangProvider) and the `lang` the wizard API resolves content for.
export default function LangToggle({ compact = false, hrefs }) {
  const { lang, setLang, t } = useT();

  const option = (code, label) => {
    const active = lang === code;
    const className = `lang-option${active ? " active" : ""}`;
    if (hrefs) {
      return (
        <a
          className={className}
          href={hrefs[code]}
          hrefLang={code}
          lang={code}
          aria-current={active ? "page" : undefined}
        >
          {label}
        </a>
      );
    }
    return (
      <button
        type="button"
        className={className}
        onClick={() => setLang(code)}
        aria-pressed={active}
        lang={code}
      >
        {label}
      </button>
    );
  };

  return (
    <div
      className={`lang-toggle${compact ? " compact" : ""}`}
      role="group"
      aria-label={t("lang.switchTo")}
    >
      {option("en", "EN")}
      {option("fa", "فا")}
    </div>
  );
}
