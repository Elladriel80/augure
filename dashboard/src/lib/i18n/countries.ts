// ISO 3166-1 alpha-2 country codes where French is the dominant language.
// Used by middleware to decide which locale to default to from Vercel's
// `x-vercel-ip-country` header.
//
// CA (Canada) is intentionally excluded: Vercel exposes the country code, not
// the region, and the anglophone majority would otherwise be served French by
// mistake. Quebec / NB / Acadian users can still override via the nav toggle.
//
// Maghreb (MA, DZ, TN) is also excluded — French is widely understood but
// Arabic is the daily lingua franca; defaulting them to FR would be presumptuous.
export const FRENCH_SPEAKING_COUNTRIES: ReadonlySet<string> = new Set([
  "FR", // France
  "BE", // Belgium
  "LU", // Luxembourg
  "MC", // Monaco
  "CH", // Switzerland
  // French overseas territories
  "GP", // Guadeloupe
  "GF", // French Guiana
  "MQ", // Martinique
  "RE", // Réunion
  "YT", // Mayotte
  "NC", // New Caledonia
  "PF", // French Polynesia
  "BL", // Saint Barthélemy
  "MF", // Saint Martin
  "PM", // Saint Pierre and Miquelon
  "WF", // Wallis and Futuna
  "TF", // French Southern Territories
  // Caribbean
  "HT", // Haiti
]);
