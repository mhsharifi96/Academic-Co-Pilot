import { localePath, translate } from "../i18n/strings.js";
import { SITE_URL } from "./server-api.js";

const SITE_NAME = "Academic Co-Pilot";

const KEYWORDS = [
  "AI research assistant",
  "academic writing AI",
  "literature review tool",
  "systematic review screening",
  "paper drafting with citations",
  "RAG for research papers",
  "thesis writing assistant",
  "data analysis for researchers",
];

const OG_LOCALE = { en: "en_US", fa: "fa_IR" };

// Branded 1200x630 social card (regenerate with scripts/make_og_image.py).
const OG_IMAGE = {
  url: "/og-image.png",
  width: 1200,
  height: 630,
  alt: "Academic Co-Pilot — from research goal to finished draft",
};

// Pricing facts for structured data. These mirror the backend and must be kept
// in sync with it: DEFAULT_USER_BALANCE (app/core/config.py — the deployed .env
// may override it) and TOPUP_AMOUNTS (app/services/topup_service.py).
const STARTER_CREDIT_USD = "0.07";
const TOPUP_AMOUNTS_USD = [5, 10, 20, 30];

// Shared defaults every root layout starts from. Page-level metadata overrides
// title/description/alternates.
export function baseMetadata(lang) {
  return {
    metadataBase: new URL(SITE_URL),
    title: {
      default: translate(lang, "landing.metaTitle"),
      template: `%s · ${SITE_NAME}`,
    },
    description: translate(lang, "landing.metaDescription"),
    applicationName: SITE_NAME,
    authors: [{ name: SITE_NAME }],
    keywords: KEYWORDS,
    icons: { icon: "/favicon.svg" },
    robots: { index: true, follow: true, "max-image-preview": "large" },
  };
}

// Metadata for one public page available in both languages. `path` is the
// unprefixed path (e.g. "/wizards/lit-review"); the Persian twin lives under /fa.
export function pageMetadata(lang, path, { title, description, absoluteTitle = false }) {
  const url = localePath(lang, path);
  return {
    title: absoluteTitle ? { absolute: title } : title,
    description,
    alternates: {
      canonical: url,
      languages: {
        en: localePath("en", path),
        fa: localePath("fa", path),
        "x-default": localePath("en", path),
      },
    },
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      url,
      title,
      description,
      locale: OG_LOCALE[lang],
      alternateLocale: Object.entries(OG_LOCALE)
        .filter(([l]) => l !== lang)
        .map(([, v]) => v),
      images: [OG_IMAGE],
    },
    twitter: { card: "summary_large_image", title, description, images: [OG_IMAGE.url] },
  };
}

// schema.org graph for the landing page: who runs the site (Organization),
// the site itself (WebSite) and the product (SoftwareApplication), linked by @id.
export function siteJsonLd(lang) {
  const orgId = `${SITE_URL}/#organization`;
  const siteId = `${SITE_URL}/#website`;
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": orgId,
        name: SITE_NAME,
        url: `${SITE_URL}/`,
        logo: {
          "@type": "ImageObject",
          url: `${SITE_URL}/logo.png`,
          width: 512,
          height: 512,
        },
      },
      {
        "@type": "WebSite",
        "@id": siteId,
        name: SITE_NAME,
        url: `${SITE_URL}/`,
        inLanguage: ["en", "fa"],
        publisher: { "@id": orgId },
      },
      {
        "@type": "SoftwareApplication",
        name: SITE_NAME,
        url: `${SITE_URL}${localePath(lang, "/")}`,
        image: `${SITE_URL}${OG_IMAGE.url}`,
        applicationCategory: "EducationalApplication",
        operatingSystem: "Web",
        inLanguage: ["en", "fa"],
        description: translate(lang, "landing.metaDescription"),
        publisher: { "@id": orgId },
        isPartOf: { "@id": siteId },
        // Pay-as-you-go: usage is metered per AI token and charged to a prepaid
        // wallet. TODO: per-use prices depend on the deployment's
        // COST_INPUT_PER_1M / COST_OUTPUT_PER_1M and are deliberately not
        // published here; add a UnitPriceSpecification once they are public.
        offers: [
          {
            "@type": "Offer",
            name: "Free sign-up",
            price: "0",
            priceCurrency: "USD",
            description: `Every new account gets $${STARTER_CREDIT_USD} of starter credit. No subscription.`,
          },
          {
            "@type": "AggregateOffer",
            name: "Wallet top-up",
            priceCurrency: "USD",
            lowPrice: String(Math.min(...TOPUP_AMOUNTS_USD)),
            highPrice: String(Math.max(...TOPUP_AMOUNTS_USD)),
            offerCount: TOPUP_AMOUNTS_USD.length,
            description:
              "Prepaid wallet top-ups, spent pay-as-you-go on AI usage. No subscription.",
          },
        ],
        featureList: [
          "Literature screening from CSV exports",
          "PDF ingestion into a searchable knowledge base",
          "Paper planning: titles, outline and sections",
          "Section-by-section drafting with IEEE, APA or Vancouver citations",
          "Sandboxed data analysis with charts",
          "English and Persian interface",
        ],
      },
    ],
  };
}

// One wizard as an ordered list of steps (schema.org HowTo).
export function wizardJsonLd(lang, wizard) {
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: wizard.title,
    description: wizard.short_description || undefined,
    inLanguage: lang,
    url: `${SITE_URL}${localePath(lang, `/wizards/${encodeURIComponent(wizard.slug)}`)}`,
    step: (wizard.steps || []).map((s, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: s.name || `${i + 1}`,
    })),
  };
}

// Serialize JSON-LD safely for an inline <script>: "<" is escaped so content
// from the database can never close the tag.
export function jsonLdScript(data) {
  return { __html: JSON.stringify(data).replace(/</g, "\\u003c") };
}
