import ReactMarkdown from "react-markdown";
import { getToken } from "../auth.js";

// Artifact paths the agent writes to and that the backend will serve.
const IMG_RE = /\.(png|jpe?g|gif|svg|webp)$/i;

function isArtifactPath(href = "") {
  const p = href.replace(/^\.\//, "");
  return p.startsWith("data/") || p.startsWith("output_figures/");
}

function toDownloadUrl(path, inline) {
  const clean = path.replace(/^\.\//, "");
  const token = getToken();
  // The token rides as a query param because <img>/link navigation can't send
  // an Authorization header.
  return (
    `/api/v1/download?path=${encodeURIComponent(clean)}` +
    (inline ? "&inline=true" : "") +
    (token ? `&token=${encodeURIComponent(token)}` : "")
  );
}

// Turn bare or backtick-wrapped artifact paths in the agent's reply into
// markdown links (or images), so react-markdown's custom renderers below can
// make them clickable.  Paths the agent already wrote as a markdown link
// target — `](path)` — are left untouched.
function linkifyArtifacts(text) {
  // `?\.?/?(data|output_figures)/…ext`?  — optionally backtick/`./`-wrapped,
  // with an optional preceding `](` (markdown link target) we must preserve.
  const re =
    /(\]\()?`?\.?\/?((?:data|output_figures)\/[^\s`)\]]+\.(?:png|jpe?g|gif|svg|webp|csv|xlsx?|pdf|txt|json|md))`?/gi;
  return text.replace(re, (match, linkPrefix, path) => {
    if (linkPrefix) return match; // already a markdown link target — leave it
    const name = path.split("/").pop();
    return IMG_RE.test(path) ? `![${name}](${path})` : `[${name}](${path})`;
  });
}

export default function Message({ role, content }) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="msg user">
        <div className="role">You</div>
        <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="msg assistant">
      <div className="role">Co-Pilot</div>
      <div className="md">
        <ReactMarkdown
          components={{
            a({ href, children, ...props }) {
              if (isArtifactPath(href)) {
                return (
                  <a
                    className="file-link"
                    href={toDownloadUrl(href, false)}
                    target="_blank"
                    rel="noreferrer"
                    download
                  >
                    📎 {children}
                  </a>
                );
              }
              return (
                <a href={href} target="_blank" rel="noreferrer" {...props}>
                  {children}
                </a>
              );
            },
            img({ src, alt }) {
              if (isArtifactPath(src)) {
                return (
                  <a
                    href={toDownloadUrl(src, true)}
                    target="_blank"
                    rel="noreferrer"
                    title="Open full size"
                  >
                    <img
                      className="file-image"
                      src={toDownloadUrl(src, true)}
                      alt={alt || "generated figure"}
                    />
                  </a>
                );
              }
              return <img src={src} alt={alt} />;
            },
          }}
        >
          {linkifyArtifacts(content)}
        </ReactMarkdown>
      </div>
    </div>
  );
}
