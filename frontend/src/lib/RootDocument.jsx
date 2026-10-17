import { Crimson_Pro, Vazirmatn } from "next/font/google";
import { isRtl } from "../i18n/strings.js";

// Self-hosted via next/font: downloaded at build time, served from our origin
// with font-display: swap and size-adjusted fallbacks (no layout shift), and no
// render-blocking request to Google. Each face is exposed as a CSS variable
// that styles.css puts at the front of its font stack. The preload is sent as
// an HTTP Link header.
//   Crimson Pro — display serif for wizard headings (incl. the landing <h1>),
//                 preloaded because it paints the largest text on the page.
//   Vazirmatn   — Persian face, used under <html dir="rtl">; not preloaded so
//                 English pages don't pay for it.
const crimson = Crimson_Pro({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
  variable: "--nf-crimson",
});
const vazirmatn = Vazirmatn({
  subsets: ["arabic", "latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  preload: false,
  variable: "--nf-vazirmatn",
});

// The <html> shell shared by both root layouts. There are two root layouts —
// `(en)` and `fa` — precisely so `lang`/`dir` are correct in the server HTML
// (a single root layout cannot see which locale segment it is rendering).
export default function RootDocument({ lang, children }) {
  return (
    <html
      lang={lang}
      dir={isRtl(lang) ? "rtl" : "ltr"}
      className={`${crimson.variable} ${vazirmatn.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f1117",
  colorScheme: "dark",
};
