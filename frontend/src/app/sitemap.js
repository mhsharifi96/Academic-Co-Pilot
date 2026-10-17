import { localePath } from "../i18n/strings.js";
import { SITE_URL, fetchWizards } from "../lib/server-api.js";

// Built per request so newly published wizards appear without a redeploy.
export const dynamic = "force-dynamic";

// Every public page in both languages, each entry cross-linked to its twin.
function entry(path, lastModified) {
  return {
    url: `${SITE_URL}${localePath("en", path)}`,
    lastModified,
    alternates: {
      languages: {
        en: `${SITE_URL}${localePath("en", path)}`,
        fa: `${SITE_URL}${localePath("fa", path)}`,
      },
    },
  };
}

export default async function sitemap() {
  const { wizards } = await fetchWizards("en");
  const now = new Date();
  const pages = [entry("/", now)];
  for (const w of wizards) {
    const path = `/wizards/${encodeURIComponent(w.slug)}`;
    pages.push(entry(path, w.updated_at ? new Date(w.updated_at) : now));
  }
  // Persian URLs as their own entries too, so they are discovered directly.
  return pages.flatMap((p) => [
    p,
    { ...p, url: p.alternates.languages.fa },
  ]);
}
