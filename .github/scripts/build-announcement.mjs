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
 * Strategy:
 *   1. Try to read an annotated tag's message.
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
  // X has no markdown — strip backticks, asterisks
  return s.replace(/[`*_]/g, '').trim();
}

function previousTag(currentTag) {
  // List all tags reachable from HEAD ordered by version, find the one before current
  const tags = sh('git tag --sort=-v:refname').split('\n').filter(Boolean);
  const idx = tags.indexOf(currentTag);
  if (idx === -1 || idx === tags.length - 1) return '';
  return tags[idx + 1];
}

function readChangelogSection(tag) {
  if (!existsSync('CHANGELOG.md')) return '';
  const content = readFileSync('CHANGELOG.md', 'utf8');
  // Look for a heading containing the version (with or without leading 'v')
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
  // Skip merge commits, skip the chore/release commits noise
  const log = sh(`git log ${range} --no-merges --pretty=format:%s`);
  if (!log) return [];
  return log
    .split('\n')
    .filter(line => line.trim() && !/^(chore|release|bump): /i.test(line));
}

function categorizeCommits(commits) {
  const buckets = {
    feat: [],
    fix: [],
    refactor: [],
    perf: [],
    docs: [],
    test: [],
    other: [],
  };
  for (const c of commits) {
    const m = c.match(/^(\w+)(\([^)]+\))?!?:\s*(.+)$/);
    if (m) {
      const type = m[1].toLowerCase();
      const msg = m[3];
      if (type in buckets) {
        buckets[type].push(msg);
        continue;
      }
    }
    buckets.other.push(c);
  }
  return buckets;
}

function pickHeadline(buckets, tag) {
  // Prefer the first feat, then first other, then a generic
  const first =
    buckets.feat[0] ||
    buckets.fix[0] ||
    buckets.refactor[0] ||
    buckets.other[0];
  if (first) return first.charAt(0).toUpperCase() + first.slice(1);
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
const annotatedMsg = sh(`git tag -l --format='%(contents)' ${TAG}`);
const changelogSection = readChangelogSection(TAG);
const commits = commitListBetween(prevTag, TAG);
const buckets = categorizeCommits(commits);

const tagDate = sh(`git log -1 --format=%cs ${TAG}`) || new Date().toISOString().slice(0, 10);
const releaseUrl = REPO_URL ? `${REPO_URL}/releases/tag/${TAG}` : '';
const compareUrl = REPO_URL && prevTag ? `${REPO_URL}/compare/${prevTag}...${TAG}` : '';

const versionLabel = isPrerelease(TAG) ? `pre-release ${TAG}` : `release ${TAG}`;
const headline = pickHeadline(buckets, TAG);

// ---------- Discord message (long-form, builder log voice) ----------

const discordLines = [];
discordLines.push(`### \`${PROJECT_NAME}\` — ${versionLabel} shipped`);
discordLines.push('');

if (annotatedMsg && annotatedMsg.length > 20) {
  // Use the maintainer's tag message verbatim — that's the most honest builder-log content
  discordLines.push(annotatedMsg.trim());
} else if (changelogSection) {
  discordLines.push(changelogSection);
} else {
  // Build from commits
  discordLines.push(`**${headline}**`);
  discordLines.push('');
  const sections = [
    ['New', buckets.feat],
    ['Fixed', buckets.fix],
    ['Improved', [...buckets.refactor, ...buckets.perf]],
    ['Docs', buckets.docs],
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

const discordMessage = discordLines.join('\n').trim();

// ---------- X message (≤280 chars, builder log voice) ----------

// X counts URLs as 23 chars (t.co wrapping) regardless of their real length.
// To keep validation simple we ensure the *raw string* stays ≤ 280, which is
// strictly more conservative than what X measures. This wastes a few chars on
// long URLs but means post-x.mjs can do a plain length check.
const X_LIMIT = 280;
const SEPARATOR = ' — ';

let xCore;
if (annotatedMsg && annotatedMsg.length > 0) {
  // Take the first line of the tag message
  xCore = annotatedMsg.split('\n').find(l => l.trim()) || headline;
} else {
  xCore = headline;
}
xCore = escapeForX(xCore);

const projectPrefix = `${PROJECT_NAME} ${TAG}`;
const tail = releaseUrl ? ` ${releaseUrl}` : '';
const overheadLen = projectPrefix.length + SEPARATOR.length + tail.length;
const available = Math.max(20, X_LIMIT - overheadLen);

let body = xCore;
if (body.length > available) body = truncate(body, available);

let xMessage = `${projectPrefix}${SEPARATOR}${body}${tail}`;
if (xMessage.length > X_LIMIT) {
  // Defensive truncate — if even the prefix + URL are too long, drop the URL.
  if (`${projectPrefix}${SEPARATOR}${body}`.length <= X_LIMIT) {
    xMessage = `${projectPrefix}${SEPARATOR}${body}`;
  } else {
    xMessage = truncate(xMessage, X_LIMIT);
  }
}

// ---------- Write files ----------

writeFileSync('announcement.discord.md', discordMessage + '\n', 'utf8');
writeFileSync('announcement.x.txt', xMessage + '\n', 'utf8');

console.log('--- Discord message ---');
console.log(discordMessage);
console.log('--- X message ---');
console.log(`${xMessage}  [${xMessage.length} chars]`);

// Step output for downstream visibility
const summary = process.env.GITHUB_STEP_SUMMARY;
if (summary) {
  appendFileSync(
    summary,
    `### Announcement built for ${TAG}\n\n` +
    `**X (${xMessage.length}/280):**\n\n\`\`\`\n${xMessage}\n\`\`\`\n\n` +
    `**Discord:**\n\n${discordMessage}\n`
  );
}
