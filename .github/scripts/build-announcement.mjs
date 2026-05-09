#!/usr/bin/env node
/**
 * build-announcement.mjs
 *
 * Generates two English announcement files from a Git tag:
 *   - announcement.discord.md  (long-form, builder-log voice, GitHub-flavored markdown)
 *   - announcement.x.txt       (≤280 chars, single tweet)
 *
 * Reads from environment:
 *   GIT_TAG          - The tag being announced (e.g. v0.1.0)
 *   REPO_URL         - Full repo URL (https://github.com/owner/repo)
 *   PROJECT_NAME     - Display name (e.g. "Augure")
 *   PROJECT_TAGLINE  - Short tagline used as fallback context
 *
 * Strategy (priority order):
 *   1. Read the annotated tag's message (the maintainer's own summary).
 *   2. Otherwise read CHANGELOG.md section for that version.
 *   3. Otherwise summarize commits between the previous tag and this one.
 *
 * No external npm dependencies. Pure Node 20+ stdlib.
 */

import { execSync } from 'node:child_process';
import { writeFileSync, existsSync, readFileSync, appendFileSync } from 'node:fs';

const TAG = process.env.GIT_TAG;
const REPO_URL = process.env.REPO_URL || '';
const PROJECT_NAME = process.env.PROJECT_NAME || 'Augure';
const PROJECT_TAGLINE = process.env.PROJECT_TAGLINE || 'Decentralized prediction markets for weather risk';

if (!TAG) {
  console.error('GIT_TAG environment variable is required.');
  process.exit(1);
}

// ---------- Helpers ----------

function sh(cmd) {
  try {
    return execSync(cmd, { encoding: 'utf8' }).trim();
  } catch (e) {
    return '';
  }
}

function escapeForX(s) {
  // X has no markdown — strip backticks, asterisks, underscores
  return s.replace(/[`*_]/g, '').trim();
}

function previousTag(currentTag) {
  // List all tags reachable from HEAD ordered by version, find the one before current
  const tags = sh('git tag --sort=-v:refname').split('\n').filter(Boolean);
  const idx = tags.indexOf(currentTag);
  if (idx === -1 || idx === tags.length - 1) return '';
  return tags[idx + 1];
}

/**
 * Read the annotated tag message robustly. Falls back across git versions and
 * across plain (non-annotated) tags. Returns the message body only — no
 * "object/type/tag/tagger" header lines, no PGP signature block.
 */
function readTagMessage(tag) {
  // Variant 1: for-each-ref returns just the contents body, cleanly.
  let out = sh(`git for-each-ref --format=%(contents) refs/tags/${tag}`);
  if (!out) {
    // Variant 2: tag -l with a format string (older fallback).
    out = sh(`git tag -l --format=%(contents) ${tag}`);
  }
  if (!out) {
    // Variant 3: cat-file. For an annotated tag the output is:
    //   object <sha>
    //   type commit
    //   tag <name>
    //   tagger <name> <email> <ts>
    //
    //   <message body>
    // For a lightweight tag, this errors out on the tag and we get nothing.
    const raw = sh(`git cat-file -p ${tag}`);
    if (raw) {
      const blank = raw.indexOf('\n\n');
      if (blank !== -1) out = raw.slice(blank + 2);
    }
  }
  if (!out) return '';
  // Strip an embedded PGP signature block if the tag was signed.
  const sigStart = out.indexOf('-----BEGIN PGP SIGNATURE-----');
  if (sigStart !== -1) out = out.slice(0, sigStart);
  return out.trim();
}

function readChangelogSection(tag) {
  if (!existsSync('CHANGELOG.md')) return '';
  const content = readFileSync('CHANGELOG.md', 'utf8');
  const versionPlain = tag.replace(/^v/, '');
  const escapedTag = tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const escapedPlain = versionPlain.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(
    `^##+\\s.*?(${escapedTag}|${escapedPlain}).*?\\n([\\s\\S]*?)(?=^##+\\s|\\Z)`,
    'm'
  );
  const m = content.match(re);
  if (!m) return '';
  return m[2].trim();
}

function commitListBetween(prevTag, currentTag) {
  const range = prevTag ? `${prevTag}..${currentTag}` : currentTag;
  const log = sh(`git log ${range} --no-merges --pretty=format:%s`);
  if (!log) return [];
  return log
    .split('\n')
    .filter(line => line.trim() && !/^(chore|release|bump): /i.test(line));
}

/**
 * Classify commits into buckets. Recognises:
 *   - Milestone squash commits matching `M\d+ — title (#n)` (the way GitHub
 *     squash-merges look when a PR title is `M3 — RoundRegistry ...`).
 *   - Conventional commits `<type>(<scope>)?: <subject>`.
 *   - Anything else lands in `other`.
 *
 * In all cases the trailing `(#n)` PR number is stripped from the displayed
 * title, since it carries no information for a release announcement.
 */
function categorizeCommits(commits) {
  const buckets = {
    milestone: [],
    feat: [],
    fix: [],
    refactor: [],
    perf: [],
    docs: [],
    test: [],
    ci: [],
    style: [],
    other: [],
  };

  const stripPrNumber = (s) => s.replace(/\s*\(#\d+\)\s*$/, '').trim();

  for (const raw of commits) {
    const c = raw.trim();
    // Milestone pattern: "M0 — ...", "M4 — ..." (em dash or hyphen).
    const milestone = c.match(/^(M\d+)\s*[—-]\s*(.+)$/);
    if (milestone) {
      buckets.milestone.push(`${milestone[1]} — ${stripPrNumber(milestone[2])}`);
      continue;
    }
    // Conventional commit: type(scope)?: subject
    const conv = c.match(/^(\w+)(\([^)]+\))?!?:\s*(.+)$/);
    if (conv) {
      const type = conv[1].toLowerCase();
      const msg = stripPrNumber(conv[3]);
      if (type in buckets) {
        buckets[type].push(msg);
        continue;
      }
    }
    buckets.other.push(stripPrNumber(c));
  }
  return buckets;
}

function pickHeadline(buckets, tagMessage, tag) {
  // 1. First non-empty line of the annotated tag message — the maintainer's
  //    own framing of the release. Strongest signal.
  if (tagMessage) {
    const firstLine = tagMessage.split('\n').find(l => l.trim());
    if (firstLine) return firstLine.trim();
  }
  // 2. The latest milestone, if any (M4, M3, ...).
  if (buckets.milestone.length) return buckets.milestone[0];
  // 3. Conventional commits, in priority order.
  const first =
    buckets.feat[0] ||
    buckets.fix[0] ||
    buckets.refactor[0] ||
    buckets.other[0];
  if (first) return first.charAt(0).toUpperCase() + first.slice(1);
  // 4. Generic fallback.
  return `Release ${tag}`;
}

function truncate(str, max) {
  if (str.length <= max) return str;
  return str.slice(0, max - 1).trimEnd() + '…';
}

function isPrerelease(tag) {
  return /-(?:alpha|beta|rc|pre|dev)/i.test(tag);
}

// ---------- Build content ----------

const prevTag = previousTag(TAG);
const tagMessage = readTagMessage(TAG);
const changelogSection = readChangelogSection(TAG);
const commits = commitListBetween(prevTag, TAG);
const buckets = categorizeCommits(commits);

const tagDate = sh(`git log -1 --format=%cs ${TAG}`) || new Date().toISOString().slice(0, 10);
const releaseUrl = REPO_URL ? `${REPO_URL}/releases/tag/${TAG}` : '';
const compareUrl = REPO_URL && prevTag ? `${REPO_URL}/compare/${prevTag}...${TAG}` : '';

const versionLabel = isPrerelease(TAG) ? `pre-release ${TAG}` : `release ${TAG}`;
const headline = pickHeadline(buckets, tagMessage, TAG);

// ---------- Discord message (≤ ~1900 chars) ----------

const DISCORD_LIMIT = 1900; // safety margin under the 2000-char webhook limit

const discordLines = [];
discordLines.push(`### \`${PROJECT_NAME}\` — ${versionLabel} shipped`);
discordLines.push('');

if (tagMessage && tagMessage.length > 20) {
  // Use the maintainer's tag message verbatim — most honest builder-log content.
  discordLines.push(tagMessage);
} else if (changelogSection) {
  discordLines.push(changelogSection);
} else {
  discordLines.push(`**${headline}**`);
  discordLines.push('');
  const sections = [
    ['Milestones', buckets.milestone],
    ['New', buckets.feat],
    ['Fixed', buckets.fix],
    ['Improved', [...buckets.refactor, ...buckets.perf]],
    ['Docs', buckets.docs],
    ['CI', buckets.ci],
  ];
  let any = false;
  for (const [label, items] of sections) {
    if (items.length === 0) continue;
    any = true;
    discordLines.push(`__${label}__`);
    for (const item of items) {
      discordLines.push(`• ${item}`);
    }
    discordLines.push('');
  }
  if (!any) {
    if (buckets.other.length) {
      discordLines.push('__Changes__');
      for (const item of buckets.other) discordLines.push(`• ${item}`);
      discordLines.push('');
    } else {
      discordLines.push('_No notable user-facing changes — internal cleanup release._');
      discordLines.push('');
    }
  }
}

discordLines.push('');
const links = [];
if (releaseUrl) links.push(`[release notes](<${releaseUrl}>)`);
if (compareUrl) links.push(`[diff](<${compareUrl}>)`);
if (links.length) discordLines.push(links.join(' · '));
discordLines.push('');
discordLines.push(`_${PROJECT_TAGLINE}._`);

let discordMessage = discordLines.join('\n').trim();
if (discordMessage.length > DISCORD_LIMIT) {
  // Truncate at the last newline before the limit, then append a follow-up link.
  const ellipsis = releaseUrl
    ? `\n\n*… [full notes](<${releaseUrl}>)*`
    : '\n\n*…*';
  const budget = DISCORD_LIMIT - ellipsis.length;
  let cut = discordMessage.lastIndexOf('\n', budget);
  if (cut < 0) cut = budget;
  discordMessage = discordMessage.slice(0, cut).trimEnd() + ellipsis;
}

// ---------- X message (≤ 280 chars) ----------

const X_LIMIT = 280;

// Source the headline from the tag message's first line when available — that
// is the maintainer's intent, expressed at tag time. Otherwise fall back to
// the auto-picked headline.
let xCore;
if (tagMessage) {
  xCore = tagMessage.split('\n').find(l => l.trim()) || headline;
} else {
  xCore = headline;
}
xCore = escapeForX(xCore);

// Optional second-line summary: if there are milestones, list them compactly.
let xExtra = '';
if (buckets.milestone.length) {
  // Strip the "Mn — " prefix and join with " · " for compactness.
  const milestoneTitles = buckets.milestone
    .map(m => m.replace(/^M\d+\s*—\s*/, ''))
    .map(m => escapeForX(m));
  xExtra = milestoneTitles.join(' · ');
}

const projectPrefix = `${PROJECT_NAME} ${TAG}`;
const tail = releaseUrl ? `\n${releaseUrl}` : '';

// Try the rich format first (3 lines), fall back progressively.
let xMessage = '';

const richLine1 = `${projectPrefix} — ${xCore}`;
const richLine2 = xExtra;
const candidate3line = [richLine1, richLine2, releaseUrl].filter(Boolean).join('\n');

if (candidate3line.length <= X_LIMIT && xExtra) {
  xMessage = candidate3line;
} else {
  // 2-line fallback: prefix + headline on line 1, URL on line 2.
  const candidate2line = `${richLine1}${tail}`;
  if (candidate2line.length <= X_LIMIT) {
    xMessage = candidate2line;
  } else {
    // Truncate the headline so the whole thing fits.
    const overheadLen = projectPrefix.length + 3 + tail.length; // " — "
    const available = Math.max(20, X_LIMIT - overheadLen);
    const truncatedCore = truncate(xCore, available);
    xMessage = `${projectPrefix} — ${truncatedCore}${tail}`;
    if (xMessage.length > X_LIMIT) {
      // Last resort: drop the URL.
      xMessage = `${projectPrefix} — ${truncatedCore}`;
      if (xMessage.length > X_LIMIT) {
        xMessage = truncate(xMessage, X_LIMIT);
      }
    }
  }
}

// ---------- Write files ----------

writeFileSync('announcement.discord.md', discordMessage + '\n', 'utf8');
writeFileSync('announcement.x.txt', xMessage + '\n', 'utf8');

console.log('--- Discord message ---');
console.log(discordMessage);
console.log(`[Discord length: ${discordMessage.length} chars / ${DISCORD_LIMIT} budget]`);
console.log('--- X message ---');
console.log(`${xMessage}  [${xMessage.length} chars / ${X_LIMIT} limit]`);

// Step output for downstream visibility
const summary = process.env.GITHUB_STEP_SUMMARY;
if (summary) {
  appendFileSync(
    summary,
    `### Announcement built for ${TAG}\n\n` +
      `**X (${xMessage.length}/${X_LIMIT}):**\n\n` +
      '```\n' + xMessage + '\n```\n\n' +
      `**Discord (${discordMessage.length}/${DISCORD_LIMIT}):**\n\n` +
      discordMessage + '\n'
  );
}
