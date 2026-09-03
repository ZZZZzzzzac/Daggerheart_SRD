import { renderPair } from "../js/render-core.mjs?v=20260903e";


self.addEventListener("message", (event) => {
  const { sequence, zh, en, language } = event.data;
  try {
    const rendered = renderPair(zh, en);
    self.postMessage({ sequence, html: rendered.html[language] });
  } catch (error) {
    self.postMessage({ sequence, error: error instanceof Error ? error.message : String(error) });
  }
});
