import { notFound } from "next/navigation";
import { LangProvider } from "../i18n.js";
import { translate } from "../i18n/strings.js";
import WizardDetail from "../components/WizardDetail.jsx";
import WizardLanding from "../components/WizardLanding.jsx";
import { fetchWizard, fetchWizards } from "./server-api.js";
import { pageMetadata } from "./seo.js";

// The public pages exist once per language (/ and /fa, /wizards/x and
// /fa/wizards/x). The route files are thin wrappers around these.

export function landingMetadata(lang) {
  return pageMetadata(lang, "/", {
    title: translate(lang, "landing.metaTitle"),
    description: translate(lang, "landing.metaDescription"),
    absoluteTitle: true,
  });
}

export async function LandingRoute({ lang }) {
  const { wizards, error } = await fetchWizards(lang);
  return (
    <LangProvider lang={lang}>
      <WizardLanding lang={lang} wizards={wizards} error={error} />
    </LangProvider>
  );
}

export async function wizardMetadata(lang, slug) {
  const wizard = await fetchWizard(slug, lang);
  if (!wizard) return { title: translate(lang, "wizard.notFound"), robots: { index: false } };
  const description =
    wizard.short_description ||
    `${wizard.title} — ${translate(lang, "wizard.steps", { n: wizard.step_count })}`;
  return pageMetadata(lang, `/wizards/${encodeURIComponent(wizard.slug)}`, {
    title: wizard.title,
    description,
  });
}

export async function WizardRoute({ lang, slug }) {
  const wizard = await fetchWizard(slug, lang);
  if (!wizard) notFound();
  return (
    <LangProvider lang={lang}>
      <WizardDetail lang={lang} wizard={wizard} />
    </LangProvider>
  );
}
