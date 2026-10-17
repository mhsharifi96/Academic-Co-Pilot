import { LandingRoute, landingMetadata } from "../../lib/pages.jsx";

// Rendered per request so the catalogue is always current and a backend
// outage at build time is never baked into the page.
export const dynamic = "force-dynamic";

export const metadata = landingMetadata("en");

export default function Page() {
  return <LandingRoute lang="en" />;
}
