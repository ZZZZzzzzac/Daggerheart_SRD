import { readFileSync } from "node:fs";

import { renderPair } from "../static/js/render-core.mjs";


const input = JSON.parse(readFileSync(0, "utf8"));
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
