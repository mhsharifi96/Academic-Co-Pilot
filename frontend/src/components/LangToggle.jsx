import { useT } from "../i18n.js";

// EN / فارسی segmented control.  Switching also flips <html dir> (handled in
// LangProvider) and changes the `lang` the wizard API resolves content for.
export default function LangToggle({ compact = false }) {
  const { lang, setLang, t } = useT();

  return (
    <div
      className={`lang-toggle${compact ? " compact" : ""}`}
      role="group"
      aria-label={t("lang.switchTo")}
    >
      <button
        type="button"
        className={`lang-option${lang === "en" ? " active" : ""}`}
        onClick={() => setLang("en")}
        aria-pressed={lang === "en"}
        lang="en"
      >
        EN
      </button>
      <button
        type="button"
        className={`lang-option${lang === "fa" ? " active" : ""}`}
        onClick={() => setLang("fa")}
        aria-pressed={lang === "fa"}
        lang="fa"
      >
        فا
      </button>
    </div>
  );
}
