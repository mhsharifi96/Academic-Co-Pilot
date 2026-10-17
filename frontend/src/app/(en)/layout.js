import "../../styles.css";
import RootDocument, { viewport } from "../../lib/RootDocument.jsx";
import { baseMetadata } from "../../lib/seo.js";

// Root layout for English public pages and for the app routes (/app, /runs).
export const metadata = baseMetadata("en");
export { viewport };

export default function EnglishRootLayout({ children }) {
  return <RootDocument lang="en">{children}</RootDocument>;
}
