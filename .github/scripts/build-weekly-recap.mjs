#!/usr/bin/env node
/**
 * build-weekly-recap.mjs
 *
 * Generates a weekly recap of repo activity for the last 7 days, in FRENCH,
 * builder-log voice. Output goes to `recap.discord.md` for the Discord poster.
 *
 * Reads from environment:
 *   PROJECT_NAME       - display name (default: "Augure")
 *   PROJECT_TAGLINE    - one-liner footer (default: weather risk tagline FR)
 *   RECAP_LOOKBACK_DAYS - integer, default 7
 *   RECAP_SKIP_IF_EMPTY - "true" (default) to exit cleanly without producing
 *                         a file when nothing meaningful happened this week.
 *
 * Strategy:
 *   1. `git log --since=N days ago --no-merges --name-only --pretty=...`
 *   2. Drop noise commits (chore/release/bump/typo-only).
 *   3. Bucket commits by *module* (predictor / contracts / docs / discord / ci…)
 *      using path heuristics on the modified files.
 *   4. Bucket within each module by conventional-commit type (feat/fix/etc).
 *   5. Render a FR markdown post with a date range and "à venir" footer.
 *
 * Output file: `recap.discord.md` (consumed by post-discord.mjs).
 * Status file: `recap.empty` (presence signals "skip Discord post").
 */

import { execSync } from 'node:child_process';
import { writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs';

const PROJECT_NAME = process.env.PROJECT_NAME || 'Augure';
const PROJECT_TAGLINE =
  process.env.PROJECT_TAGLINE ||
  'Marchés prédictifs décentralisés pour le risque météo';
// SECURITY: clamp the lookback to a sane range. RECAP_LOOKBACK_DAYS can
// originate from a workflow_dispatch input; parseInt drops trailing junk
// but we still want to reject NaN and any value outside [1, 365] so the
// number that lands in the shell substitution below is always a plain
// positive integer.
const _rawLookback = Number.parseInt(process.env.RECAP_LOOKBACK_DAYS || '7', 10);
const LOOKBACK_DAYS =
  Number.isFinite(_rawLookback) && _rawLookback >= 1 && _rawLookback <= 365
    ? _rawLookback
    : 7;
const SKIP_IF_EMPTY = (process.env.RECAP_SKIP_IF_EMPTY ?? 'true') === 'true';

// ---------- Helpers ----------

function sh(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf8' });
  } catch {
    return '';
  }
}

function frDate(d) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'long',
  }).format(d);
}

function frDateLong(d) {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(d);
}

// ---------- Collect commits ----------

const since = `${LOOKBACK_DAYS} days ago`;
// Custom record separator so multiline subjects don't break parsing.
const SEP = '<<<COMMIT_SEP>>>';
const FIELD = '<<<F>>>';

const raw = sh(
  `git log --since="${since}" --no-merges --name-only ` +
    `--pretty=format:"${SEP}%H${FIELD}%s${FIELD}%an${FIELD}%cs"`
);

if (!raw.trim()) {
  handleEmpty('Aucun commit poussé sur main cette semaine.');
  process.exit(0);
}

// Parse: split on SEP, skip the empty leading chunk
const records = raw.split(SEP).slice(1);

const NOISE_PREFIXES = /^(chore|release|bump|typo|style|wip)(\([^)]+\))?!?:\s*/i;

const commits = [];
for (const rec of records) {
  const lines = rec.split('\n');
  const header = lines.shift() || '';
  const [hash, subject, author, date] = header.split(FIELD);
  if (!subject) continue;
  if (NOISE_PREFIXES.test(subject)) continue;

  const files = lines.map(l => l.trim()).filter(Boolean);
  commits.push({ hash, subject, author, date, files });
}

if (commits.length === 0) {
  handleEmpty('Que des commits de routine cette semaine (chore/release/typo).');
  process.exit(0);
}

// ---------- Bucket by module ----------

// Map file path → module label (FR). First match wins.
const MODULE_RULES = [
  [/^predictor\//, 'Predictor'],
  [/^contracts\/(?!lib\/)/, 'Contracts'],          // exclude vendored lib/
  [/^contracts\/lib\//, null],                      // ignore — vendored deps
  [/^contracts\//, 'Contracts'],
  [/^site\//, 'Site'],
  [/^docs\//, 'Docs'],
  [/^rounds\//, 'Rounds'],
  [/^\.github\//, 'CI / Infra'],
  [/discord/i, 'Discord'],                          // root-level discord-* files
  [/(audit|content[-_]pack|checklist|contacts|status)/i, 'Comm / Process'],
  [/\.md$/, 'Docs'],                                // any other markdown
];

function moduleFor(file) {
  for (const [re, label] of MODULE_RULES) {
    if (re.test(file)) return label;
  }
  return 'Divers';
}

function typeOf(subject) {
  const m = subject.match(/^(\w+)(\([^)]+\))?!?:\s*/);
  if (!m) return 'other';
  return m[1].toLowerCase();
}

function shortSubject(subject) {
  // Drop the "type(scope): " prefix for display
  return subject.replace(/^\w+(\([^)]+\))?!?:\s*/, '').trim();
}

// commit may touch several modules → count it in each, but try to attribute it
// to a "primary" module = the one with the most files in this commit.
const moduleBuckets = new Map(); // module -> { feat: [], fix: [], other: [] }

function addToModule(mod, type, msg) {
  if (!mod) return;
  if (!moduleBuckets.has(mod)) {
    moduleBuckets.set(mod, { feat: [], fix: [], other: [] });
  }
  const b = moduleBuckets.get(mod);
  const list = type === 'feat' ? b.feat : type === 'fix' ? b.fix : b.other;
  if (!list.includes(msg)) list.push(msg);
}

for (const c of commits) {
  const type = typeOf(c.subject);
  const subj = shortSubject(c.subject);
  if (c.files.length === 0) {
    // No file info (rare) — bucket under Divers
    addToModule('Divers', type, subj);
    continue;
  }
  const counts = new Map();
  for (const f of c.files) {
    const m = moduleFor(f);
    if (!m) continue;
    counts.set(m, (counts.get(m) || 0) + 1);
  }
  if (counts.size === 0) {
    addToModule('Divers', type, subj);
    continue;
  }
  // Primary = max files
  const primary = [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
  addToModule(primary, type, subj);
}

// ---------- Tags / releases this week ----------

const tagsThisWeek = sh(
  `git tag --sort=-creatordate ` +
    `--format='%(refname:short)|%(creatordate:short)|%(contents:subject)'`
)
  .split('\n')
  .filter(Boolean)
  .map(line => {
    const [name, date, subject] = line.split('|');
    return { name, date, subject };
  })
  .filter(t => {
    const cutoff = Date.now() - LOOKBACK_DAYS * 24 * 3600 * 1000;
    return new Date(t.date).getTime() >= cutoff;
  });

// ---------- Render ----------

const now = new Date();
const start = new Date(now.getTime() - LOOKBACK_DAYS * 24 * 3600 * 1000);

const out = [];
out.push(
  `### \`${PROJECT_NAME}\` — semaine du ${frDate(start)} au ${frDateLong(now)}`
);
out.push('');
out.push('Récap de ce qui a bougé sur le repo cette semaine.');
out.push('');

// Display order — predictable, important modules first
const ORDER = [
  'Predictor',
  'Contracts',
  'Rounds',
  'Site',
  'Docs',
  'Discord',
  'Comm / Process',
  'CI / Infra',
  'Divers',
];

const renderedModules = [];
for (const mod of ORDER) {
  if (!moduleBuckets.has(mod)) continue;
  const b = moduleBuckets.get(mod);
  const lines = [];
  for (const item of b.feat) lines.push(`• ${item}`);
  for (const item of b.fix) lines.push(`• Correctif : ${item}`);
  for (const item of b.other) lines.push(`• ${item}`);
  if (lines.length === 0) continue;

  out.push(`__${mod}__`);
  out.push(...lines);
  out.push('');
  renderedModules.push(mod);
}

if (renderedModules.length === 0) {
  handleEmpty('Activité trop fragmentée pour un récap propre cette semaine.');
  process.exit(0);
}

if (tagsThisWeek.length > 0) {
  out.push(`__Releases taguées cette semaine__`);
  for (const t of tagsThisWeek) {
    const subjectStr = t.subject ? ` — ${t.subject}` : '';
    out.push(`• \`${t.name}\`${subjectStr}`);
  }
  out.push('');
}

out.push(`_${PROJECT_TAGLINE}._`);

const message = out.join('\n').trim();

writeFileSync('recap.discord.md', message + '\n', 'utf8');

console.log('--- Recap built ---');
console.log(message);
console.log(`--- ${commits.length} commits, ${renderedModules.length} modules ---`);

const summary = process.env.GITHUB_STEP_SUMMARY;
if (summary) {
  appendFileSync(
    summary,
    `### Weekly recap built\n\n` +
      `${commits.length} commits sur ${LOOKBACK_DAYS} jours, ${renderedModules.length} modules.\n\n` +
      `\`\`\`\n${message}\n\`\`\`\n`
  );
}

// ---------- Empty handler ----------

function handleEmpty(reason) {
  console.log(`No recap to publish: ${reason}`);
  if (SKIP_IF_EMPTY) {
    writeFileSync('recap.empty', reason, 'utf8');
    const summary = process.env.GITHUB_STEP_SUMMARY;
    if (summary) {
      appendFileSync(
        summary,
        `### Weekly recap skipped\n\n${reason}\n`
      );
    }
  } else {
    // Force a minimal post
    const minimal = [
      `### \`${PROJECT_NAME}\` — récap hebdo`,
      '',
      `_${reason} On reprend les choses sérieuses la semaine prochaine._`,
      '',
      `_${PROJECT_TAGLINE}._`,
    ].join('\n');
    writeFileSync('recap.discord.md', minimal + '\n', 'utf8');
  }
}
