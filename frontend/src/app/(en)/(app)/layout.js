import { LangProvider } from "../../../i18n.js";

// The signed-in application. Its content is per-user and client-rendered, so
// it is kept out of search indexes; the public pages carry the SEO weight.
export const metadata = {
  title: "App",
  robots: { index: false, follow: false },
};

export default function AppLayout({ children }) {
  return <LangProvider>{children}</LangProvider>;
}
