import { cookies } from "next/headers";

import { en, type Dictionary } from "./locales/en";
import { fr } from "./locales/fr";

export type Locale = "en" | "fr";

export const LOCALE_COOKIE = "aratea-locale";
export const DEFAULT_LOCALE: Locale = "en";

const DICTIONARIES: Record<Locale, Dictionary> = { en, fr };

/**
 * Read the user's locale from the `aratea-locale` cookie.
 * The cookie is set by `middleware.ts` from the Vercel geo header on first
 * visit, and can be overridden by the user via the nav toggle.
 *
 * Calling this forces the page into dynamic rendering (cookies() is a dynamic
 * function in App Router). That's acceptable for this dashboard — there is no
 * CDN cache hit rate to preserve and on-chain reads are already per-request.
 */
export async function getLocale(): Promise<Locale> {
  const store = await cookies();
  const value = store.get(LOCALE_COOKIE)?.value;
  return value === "fr" ? "fr" : "en";
}

/**
 * Return the translation dictionary for the current request.
 * Use in server components: `const dict = await getDict();`.
 */
export async function getDict(): Promise<Dictionary> {
  const locale = await getLocale();
  return DICTIONARIES[locale];
}

/**
 * Same as getDict but returns the locale alongside, to avoid two awaits when
 * a component also needs the raw locale code (e.g. for date formatting).
 */
export async function getDictAndLocale(): Promise<{
  dict: Dictionary;
  locale: Locale;
}> {
  const locale = await getLocale();
  return { dict: DICTIONARIES[locale], locale };
}
