// The app's inline stroke icon set.
//
// Deliberately SVG rather than the emoji used elsewhere in this app: emoji
// render differently on every platform, can't inherit colour, and read as
// decoration rather than iconography at card sizes.
//
// An admin picks one by storing its key in `Wizard.icon`; an unknown or missing
// key falls back to `compass`.

const PATHS = {
  compass: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m15.5 8.5-2.1 5-5 2.1 2.1-5z" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.6-3.6" />
    </>
  ),
  document: (
    <>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6M9 17h4" />
    </>
  ),
  layers: (
    <>
      <path d="m12 3 9 5-9 5-9-5z" />
      <path d="m3 13 9 5 9-5" />
    </>
  ),
  chart: (
    <>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </>
  ),
  beaker: (
    <>
      <path d="M9 3v6.5L4.2 18A2 2 0 0 0 6 21h12a2 2 0 0 0 1.8-3L15 9.5V3" />
      <path d="M8 3h8M6.5 14h11" />
    </>
  ),
  quote: (
    <>
      <path d="M9 7H5.5A2.5 2.5 0 0 0 3 9.5v2A2.5 2.5 0 0 0 5.5 14H7v1a3 3 0 0 1-3 3" />
      <path d="M20 7h-3.5A2.5 2.5 0 0 0 14 9.5v2a2.5 2.5 0 0 0 2.5 2.5H18v1a3 3 0 0 1-3 3" />
    </>
  ),
  sparkles: (
    <>
      <path d="m12 3 1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9z" />
      <path d="M18.5 15.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" />
    </>
  ),
  check: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12.2 2.4 2.4 4.6-4.8" />
    </>
  ),
  arrow: <path d="M5 12h13m-5-6 6 6-6 6" />,
  play: <path d="M8 5.5v13l11-6.5z" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5V12l3 1.8" />
    </>
  ),
  pencil: (
    <>
      <path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17v3z" />
      <path d="M13.5 6.5l4 4" />
    </>
  ),
  close: <path d="m6 6 12 12M18 6 6 18" />,
  paperclip: (
    <path d="M20.5 11.5 12 20a5 5 0 0 1-7-7l8.5-8.5a3.5 3.5 0 0 1 5 5L10 18a2 2 0 0 1-3-3l8-8" />
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  send: <path d="M4.5 12 20 4.5 15.5 20l-3.6-5.9L4.5 12z" />,
  chevronDown: <path d="m6 9.5 6 6 6-6" />,
};

export const WIZARD_ICON_KEYS = [
  "compass",
  "search",
  "document",
  "layers",
  "chart",
  "beaker",
  "quote",
  "sparkles",
];

export default function Icon({ name, size = 24, className = "" }) {
  const path = PATHS[name] || PATHS.compass;
  return (
    <svg
      className={`wz-icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {path}
    </svg>
  );
}
