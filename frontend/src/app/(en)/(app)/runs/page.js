"use client";

import RequireAuth from "../../../../components/AuthGate.jsx";
import WizardRunsPage from "../../../../components/WizardRunsPage.jsx";

export default function RunsPage() {
  return (
    <RequireAuth>
      <WizardRunsPage />
    </RequireAuth>
  );
}
