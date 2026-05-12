import { NextRequest, NextResponse } from "next/server";

import { FRENCH_SPEAKING_COUNTRIES } from "./src/lib/i18n/countries";

const LOCALE_COOKIE = "aratea-locale";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

/**
 * Detect the visitor's country from Vercel's `x-vercel-ip-country` header
 * (auto-injected on Vercel deployments). If the country is in our
 * French-speaking list AND the user has not yet set a locale cookie,
 * default to `fr`. Otherwise default to `en`.
 *
 * The cookie is also injected into the current request so the very first page
 * render of a fresh visitor already gets the right language — no flash of EN
 * before the FR cookie kicks in on the next request.
 */
export function middleware(request: NextRequest) {
  // User-set or previously-detected — never override.
  if (request.cookies.has(LOCALE_COOKIE)) {
    return NextResponse.next();
  }

  const country = request.headers.get("x-vercel-ip-country")?.toUpperCase() ?? "";
  const locale = FRENCH_SPEAKING_COUNTRIES.has(country) ? "fr" : "en";

  // Make the cookie visible to this request's server components.
  request.cookies.set(LOCALE_COOKIE, locale);

  const response = NextResponse.next({
    request: { headers: request.headers },
  });

  // Persist for future requests.
  response.cookies.set(LOCALE_COOKIE, locale, {
    path: "/",
    maxAge: ONE_YEAR_SECONDS,
    sameSite: "lax",
    httpOnly: false, // the LocaleToggle (client) needs to read & rewrite it
  });

  return response;
}

// Skip Next.js internals and static assets — middleware only needs to run for
// page requests where the locale cookie matters.
export const config = {
  matcher: ["/((?!_next/|api/|.*\\..*).*)"],
};
