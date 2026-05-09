#!/usr/bin/env node
/**
 * post-x.mjs
 *
 * Posts the contents of $X_MESSAGE_PATH as a tweet to X (Twitter) v2 API
 * using OAuth 1.0a User Context.
 *
 * Reads from environment:
 *   X_API_KEY               - app consumer key
 *   X_API_SECRET            - app consumer secret
 *   X_ACCESS_TOKEN          - user access token
 *   X_ACCESS_TOKEN_SECRET   - user access token secret
 *   X_MESSAGE_PATH          - path to the .txt file containing the tweet
 *
 * Notes:
 *   - For JSON bodies, OAuth 1.0a does NOT include the body in the signature
 *     base string. Only the OAuth params + URL + method are signed.
 *   - X API tier "Free" allows ~1500 tweets/month from a User Context;
 *     "Basic" tier ($200/mo as of 2024) raises the limit and adds replies.
 *   - We do not fail the whole job if posting fails — Discord may have already
 *     succeeded. We exit with code 1 only after logging clearly.
 */

import { readFileSync } from 'node:fs';
import { createHmac, randomBytes } from 'node:crypto';

const KEY = process.env.X_API_KEY;
const SECRET = process.env.X_API_SECRET;
const TOKEN = process.env.X_ACCESS_TOKEN;
const TOKEN_SECRET = process.env.X_ACCESS_TOKEN_SECRET;
const MESSAGE_PATH = process.env.X_MESSAGE_PATH || 'announcement.x.txt';

if (!KEY || !SECRET || !TOKEN || !TOKEN_SECRET) {
  console.error('X API credentials missing (X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_TOKEN_SECRET).');
  console.error('Skipping X post. Configure repo secrets to enable.');
  process.exit(0); // soft-skip — Discord may still succeed in a sibling step
}

const tweetText = readFileSync(MESSAGE_PATH, 'utf8').trim();
if (!tweetText) {
  console.error('Empty tweet file, nothing to post.');
  process.exit(1);
}
if (tweetText.length > 280) {
  console.error(`Tweet too long: ${tweetText.length} chars (limit 280). Refusing to post.`);
  process.exit(1);
}

// ---------- OAuth 1.0a signing (HMAC-SHA1) ----------

// RFC 3986 percent-encoding (stricter than encodeURIComponent for !*'()).
function pct(s) {
  return encodeURIComponent(s).replace(
    /[!*'()]/g,
    c => '%' + c.charCodeAt(0).toString(16).toUpperCase()
  );
}

function buildAuthHeader({ method, url }) {
  const oauth = {
    oauth_consumer_key: KEY,
    oauth_nonce: randomBytes(16).toString('hex'),
    oauth_signature_method: 'HMAC-SHA1',
    oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
    oauth_token: TOKEN,
    oauth_version: '1.0',
  };

  // For JSON body requests, only oauth_* params are part of the signature base
  const paramString = Object.keys(oauth)
    .sort()
    .map(k => `${pct(k)}=${pct(oauth[k])}`)
    .join('&');

  const baseString = [
    method.toUpperCase(),
    pct(url),
    pct(paramString),
  ].join('&');

  const signingKey = `${pct(SECRET)}&${pct(TOKEN_SECRET)}`;
  const signature = createHmac('sha1', signingKey).update(baseString).digest('base64');
  oauth.oauth_signature = signature;

  const header =
    'OAuth ' +
    Object.keys(oauth)
      .sort()
      .map(k => `${pct(k)}="${pct(oauth[k])}"`)
      .join(', ');

  return header;
}

// ---------- Send tweet ----------

const url = 'https://api.twitter.com/2/tweets';
const authHeader = buildAuthHeader({ method: 'POST', url });

const res = await fetch(url, {
  method: 'POST',
  headers: {
    'Authorization': authHeader,
    'Content-Type': 'application/json',
    'User-Agent': 'augure-announce-bot/1.0',
  },
  body: JSON.stringify({ text: tweetText }),
});

const body = await res.text();

if (!res.ok) {
  console.error(`X POST failed (${res.status}): ${body}`);
  // Surface common failure modes
  if (res.status === 401) {
    console.error('Hint: check that the access token belongs to a project-attached app, and that the app has Read+Write permissions enabled in the X dev portal.');
  } else if (res.status === 403) {
    console.error('Hint: 403 often means the X API access tier does not allow posting (e.g. tier was downgraded), or the tweet duplicates a recent one.');
  } else if (res.status === 429) {
    console.error('Hint: 429 = rate limited. Free tier ~50 tweets / 24h.');
  }
  process.exit(1);
}

let parsed = {};
try { parsed = JSON.parse(body); } catch {}
const id = parsed?.data?.id;
console.log(`Tweet posted: ${id ? `https://x.com/i/status/${id}` : '(no id returned)'}`);
console.log(body);
