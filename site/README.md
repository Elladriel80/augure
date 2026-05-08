# site/

Public landing page for Augure. Single-file HTML, no build step.

**Live:** [augure-ai.netlify.app](https://augure-ai.netlify.app/)

## Files

- `index.html` — the landing. Bilingual (FR/EN) with IP-based language detection on first visit, language preference persisted in `localStorage`. Three CTAs: Discord, GitHub, Notion whitepaper.

## Edit

Public links live at the top of the inline `<script>` (`const LINKS = {...}`). i18n strings are in the `I18N` object below it.

## Deploy

Currently deployed via Netlify drag-and-drop of this folder. To switch to git-driven deploys: in Netlify, *Site settings → Build & deploy → Link repository* → select `Elladriel80/augure` → set publish directory to `site/` → no build command.
