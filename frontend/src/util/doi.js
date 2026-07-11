// Detect DOIs in assistant messages so we can offer a "Get PDF" action.
// Mirrors the backend DOI shape (app/tools/literature.py:_DOI_RE); the backend
// re-validates and normalises whatever we submit, so this only needs to be a
// good-enough detector.
const DOI_RE = /\b10\.\d{4,9}\/[^\s"'<>()\[\]]+/gi;

// Trailing sentence punctuation that shouldn't be part of the DOI.
const TRAILING = /[.,;:)\]]+$/;

export function extractDois(text) {
  if (!text) return [];
  const seen = new Set();
  const out = [];
  let m;
  DOI_RE.lastIndex = 0;
  while ((m = DOI_RE.exec(text)) !== null) {
    const doi = m[0].replace(TRAILING, "");
    if (doi && !seen.has(doi)) {
      seen.add(doi);
      out.push(doi);
    }
  }
  return out;
}
