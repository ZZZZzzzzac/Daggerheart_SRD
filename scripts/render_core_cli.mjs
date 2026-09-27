import { readFileSync } from "node:fs";

import { renderPair } from "../static/js/render-core.mjs";
import { parseGlossary, serializeGlossary } from "../static/js/glossary-core.mjs";


const input = JSON.parse(readFileSync(0, "utf8"));
if (input.mode === "glossary") {
  process.stdout.write(JSON.stringify(parseGlossary(input.markdown)));
  process.exit(0);
}
if (input.mode === "serialize-glossary") {
  process.stdout.write(serializeGlossary(input.terms));
  process.exit(0);
}
if (!Array.isArray(input.documents)) {
  throw new TypeError("documents must be an array");
}

const documents = input.documents.map((document) => {
  if (typeof document.zh !== "string" || typeof document.en !== "string") {
    throw new TypeError("each document must contain zh and en strings");
  }
  return renderPair(document.zh, document.en, { pagePath: document.pagePath || "" });
});

process.stdout.write(JSON.stringify({ documents }));
