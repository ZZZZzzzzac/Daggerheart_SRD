# SRD Publishing

This context covers editing, rendering, validating, and publishing the bilingual SRD.

## Language

**Page Draft**:
One editable language file together with the server version from which it was loaded. A page draft exists only in the current browser session.
_Avoid_: Unsaved page, temporary page

**Change Set**:
All dirty page drafts submitted by one editor in one publication attempt. A change set succeeds or fails as a whole.
_Avoid_: Batch save, multiple saves

**Publication**:
The atomic transition that validates one change set, rebuilds the complete site, replaces the live content and site, and records one local Git commit.
_Avoid_: Save, upload

**Render Core**:
The canonical JavaScript module that converts bilingual Markdown into article HTML, stable anchors, and diagnostics in both the browser and the server build.
_Avoid_: Preview renderer, server renderer

**Git Sync**:
The asynchronous push of an already successful local publication to GitHub. Git Sync does not determine whether the publication succeeded.
_Avoid_: Publish, deployment
