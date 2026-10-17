import Link from "next/link";
import { localePath, translate } from "../../i18n/strings.js";

export const metadata = { robots: { index: false } };

export default function NotFound() {
  return (
    <div className="wz-landing">
      <main className="wz-detail">
        <div className="wz-empty">
          <h1 className="wz-detail-title">404</h1>
          <p>{translate("en", "wizard.notFound")}</p>
          <Link className="wz-btn ghost" href={localePath("en", "/")}>
            {translate("en", "wizard.back")}
          </Link>
        </div>
      </main>
    </div>
  );
}
