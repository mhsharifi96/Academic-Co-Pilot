import "../../styles.css";
import RootDocument, { viewport } from "../../lib/RootDocument.jsx";
import { baseMetadata } from "../../lib/seo.js";

// Root layout for the Persian public pages: server-rendered lang="fa" dir="rtl".
export const metadata = baseMetadata("fa");
export { viewport };

export default function PersianRootLayout({ children }) {
  return <RootDocument lang="fa">{children}</RootDocument>;
}
