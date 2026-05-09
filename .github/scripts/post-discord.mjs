#!/usr/bin/env node
/**
 * post-discord.mjs
 *
 * Posts the contents of $DISCORD_MESSAGE_PATH to a Discord webhook.
 * Splits into multiple messages if content exceeds 2000 chars.
 *
 * Reads from environment:
 *   DISCORD_WEBHOOK_URL    - the Discord channel webhook URL
 *   DISCORD_MESSAGE_PATH   - path to the markdown file to post
 */

import { readFileSync } from 'node:fs';

const WEBHOOK = process.env.DISCORD_WEBHOOK_URL;
const PATH = process.env.DISCORD_MESSAGE_PATH || 'announcement.discord.md';
const DISCORD_LIMIT = 2000;

if (!WEBHOOK) {
  console.error('DISCORD_WEBHOOK_URL is not set. Skipping Discord post.');
  process.exit(0); // do not fail the workflow — let the run still report success for X
}

const content = readFileSync(PATH, 'utf8').trim();
if (!content) {
  console.error('Empty announcement file, nothing to post.');
  process.exit(1);
}

// Split on blank lines if too long
function chunk(text) {
  if (text.length <= DISCORD_LIMIT) return [text];
  const chunks = [];
  const paragraphs = text.split(/\n\n+/);
  let buf = '';
  for (const p of paragraphs) {
    if ((buf + '\n\n' + p).length > DISCORD_LIMIT) {
      if (buf) chunks.push(buf);
      // If a single paragraph itself is too long, hard-split
      if (p.length > DISCORD_LIMIT) {
        for (let i = 0; i < p.length; i += DISCORD_LIMIT) {
          chunks.push(p.slice(i, i + DISCORD_LIMIT));
        }
        buf = '';
      } else {
        buf = p;
      }
    } else {
      buf = buf ? buf + '\n\n' + p : p;
    }
  }
  if (buf) chunks.push(buf);
  return chunks;
}

const parts = chunk(content);

for (let i = 0; i < parts.length; i++) {
  const body = JSON.stringify({
    content: parts[i],
    allowed_mentions: { parse: [] }, // never @everyone or role pings from CI
  });

  const res = await fetch(WEBHOOK, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });

  if (!res.ok) {
    const text = await res.text();
    console.error(`Discord POST failed (${res.status}): ${text}`);
    process.exit(1);
  }
  console.log(`Discord part ${i + 1}/${parts.length} posted (${parts[i].length} chars).`);

  // Be polite to Discord rate limits between chunks
  if (i < parts.length - 1) await new Promise(r => setTimeout(r, 1500));
}

console.log('Discord post complete.');
