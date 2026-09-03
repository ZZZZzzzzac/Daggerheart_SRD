# Share one JavaScript render core across browser preview and server publication

The editor must preview large pages without network requests while preserving exact agreement with the published site. The browser and the server build therefore call the same JavaScript Render Core; the browser renders Page Drafts locally, while the server independently renders the submitted Change Set during Publication instead of trusting browser-generated HTML. A Change Set may contain Chinese and English drafts from multiple pages, is validated and published atomically, produces one local Git commit, and is followed by asynchronous Git Sync.

## Consequences

- The production server requires a supported Node.js LTS runtime only while building a Publication; Node.js is not a resident service.
- Python continues to coordinate manifests, candidate directories, Hugo, validation, atomic replacement, Git commits, and Git Sync.
- The browser caches loaded Page Drafts only for its current session and sends no preview requests while editing.
- Render Core dependencies are self-hosted and pinned; browser and server tests exercise the same rendering fixtures through the module interface.
