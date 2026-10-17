import { WizardRoute, wizardMetadata } from "../../../../lib/pages.jsx";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { slug } = await params;
  return wizardMetadata("fa", slug);
}

export default async function Page({ params }) {
  const { slug } = await params;
  return <WizardRoute lang="fa" slug={slug} />;
}
