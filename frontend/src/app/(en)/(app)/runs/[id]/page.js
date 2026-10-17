"use client";

import { useParams } from "next/navigation";
import RequireAuth from "../../../../../components/AuthGate.jsx";
import WizardRunner from "../../../../../components/WizardRunner.jsx";

export default function RunPage() {
  const { id } = useParams();
  return (
    <RequireAuth>
      {/* Keyed so switching runs remounts with fresh state. */}
      <WizardRunner key={id} runId={decodeURIComponent(id)} />
    </RequireAuth>
  );
}
