/**
 * NWS (US National Weather Service) API client.
 *
 * Documents what the keeper *expects* to fetch off-chain and how it maps to the
 * on-chain Measurement struct:
 *
 *   GET ${NWS_BASE_URL}/stations/${stationId}/observations/latest
 *   →  properties.temperature.value     : number | null     (in °C, per unitCode)
 *      properties.temperature.unitCode  : "wmoUnit:degC"    (asserted, never converted)
 *      properties.timestamp             : ISO 8601 string   (UTC)
 *
 * Anything else (null value, unitCode mismatch, parse failure) is rejected explicitly.
 * The keeper does NOT attempt unit conversion from degF/K — that's a class of bug we
 * deliberately avoid.
 *
 * Per NWS policy, every request MUST set a User-Agent identifying the caller. The
 * project repo URL satisfies the policy without leaking a personal email.
 *
 *   https://www.weather.gov/documentation/services-web-api
 */

export const NWS_USER_AGENT = "aratea-oracle-poc/0.1 (https://github.com/Elladriel80/Aratea)";

export const NWS_REQUEST_HEADERS = {
    accept: "application/geo+json",
    "user-agent": NWS_USER_AGENT,
} as const;

/** Subset of the NWS latest-observation response actually consumed downstream. */
export interface NwsLatestObservation {
    /** Full URL the observation was fetched from. Forwarded to Reclaim zkFetch as the proven URL. */
    url: string;
    /** Raw JSON body returned by NWS. Forwarded to zkFetch for content hashing. */
    rawJson: string;
    /** Temperature in milliCelsius (int-friendly), the unit ReclaimWeatherSource stores on-chain. */
    temperatureMilliCelsius: number;
    /** Unix timestamp (seconds, UTC) of the measurement per NWS. */
    timestampUnixSeconds: number;
}

/** Reasons the keeper rejects an observation. Each maps to a structured log line. */
export type NwsRejectionReason =
    | "http_error"
    | "json_parse_error"
    | "missing_properties"
    | "missing_temperature_value"
    | "wrong_temperature_unit"
    | "missing_timestamp"
    | "invalid_timestamp";

export class NwsRejection extends Error {
    constructor(
        public readonly reason: NwsRejectionReason,
        message: string,
        public readonly context: Record<string, unknown> = {},
    ) {
        super(message);
        this.name = "NwsRejection";
    }
}

/** The only temperature unit code the keeper accepts. NWS uses WMO unit codes. */
const EXPECTED_TEMP_UNIT_CODE = "wmoUnit:degC";

export interface FetchOptions {
    baseUrl: string;
    stationId: string;
    /** Optional fetch implementation override, mainly for tests. */
    fetchImpl?: typeof fetch;
}

/**
 * Fetch the latest observation for an NWS station and normalise it for the keeper.
 * Throws NwsRejection on any disqualifying condition; never silently coerces.
 */
export async function fetchLatestObservation(opts: FetchOptions): Promise<NwsLatestObservation> {
    const url = `${opts.baseUrl}/stations/${encodeURIComponent(opts.stationId)}/observations/latest`;
    const fetchFn = opts.fetchImpl ?? fetch;

    const response = await fetchFn(url, {headers: NWS_REQUEST_HEADERS});
    if (!response.ok) {
        throw new NwsRejection("http_error", `NWS responded with HTTP ${response.status}`, {
            url,
            status: response.status,
        });
    }

    const rawJson = await response.text();
    let parsed: unknown;
    try {
        parsed = JSON.parse(rawJson);
    } catch (err) {
        throw new NwsRejection("json_parse_error", "NWS body is not valid JSON", {
            url,
            error: err instanceof Error ? err.message : String(err),
        });
    }

    const props = extractProperties(parsed);
    if (!props) {
        throw new NwsRejection("missing_properties", "NWS payload has no `properties` object", {url});
    }

    const temperature = props["temperature"];
    if (!isObject(temperature)) {
        throw new NwsRejection("missing_temperature_value", "`properties.temperature` is not an object", {url});
    }

    const unitCode = temperature["unitCode"];
    if (unitCode !== EXPECTED_TEMP_UNIT_CODE) {
        throw new NwsRejection(
            "wrong_temperature_unit",
            `Expected temperature unitCode "${EXPECTED_TEMP_UNIT_CODE}", got "${String(unitCode)}". Refusing to convert.`,
            {url, unitCode},
        );
    }

    const valueCelsius = temperature["value"];
    if (typeof valueCelsius !== "number" || !Number.isFinite(valueCelsius)) {
        throw new NwsRejection(
            "missing_temperature_value",
            "`properties.temperature.value` is null or non-numeric (station did not report)",
            {url, value: valueCelsius},
        );
    }

    const timestampString = props["timestamp"];
    if (typeof timestampString !== "string") {
        throw new NwsRejection("missing_timestamp", "`properties.timestamp` is not a string", {url});
    }
    const timestampMs = Date.parse(timestampString);
    if (!Number.isFinite(timestampMs)) {
        throw new NwsRejection("invalid_timestamp", `Could not parse ISO timestamp "${timestampString}"`, {url});
    }

    const temperatureMilliCelsius = Math.round(valueCelsius * 1000);
    const timestampUnixSeconds = Math.floor(timestampMs / 1000);

    return {
        url,
        rawJson,
        temperatureMilliCelsius,
        timestampUnixSeconds,
    };
}

function extractProperties(payload: unknown): Record<string, unknown> | null {
    if (!isObject(payload)) return null;
    const props = payload["properties"];
    return isObject(props) ? props : null;
}

function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
