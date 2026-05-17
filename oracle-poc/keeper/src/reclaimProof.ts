/**
 * Reclaim Protocol zkFetch integration.
 *
 * Wraps three things:
 *   1. ReclaimClient.zkFetch  → generates a zkProof on an HTTPS GET to a public URL
 *      (no provider needed; the catalogue at dev.reclaimprotocol.org has no weather
 *      provider, but zkFetch sidesteps that, cf. SPEC.md).
 *   2. verifyProof            → locally re-checks the witness signatures over the
 *      claim hash before pushing on-chain. The current js-sdk version exposes
 *      `verifyProof(proof, allowAiWitness?)` returning a plain `Promise<boolean>`;
 *      the older `dangerouslyDisableContentValidation` flag is gone. See
 *      docs/POC-NOTES.md for the rationale on what this check covers and what it
 *      does NOT cover (it does NOT re-fetch the upstream URL).
 *   3. transformForOnchain    → produces the `(claimInfo, signedClaim)` tuple shape
 *      that `IReclaim.Proof` expects in Solidity.
 *
 * The encoded blob this module emits matches the ABI tuple ReclaimWeatherSource
 * decodes in `submitMeasurement`:
 *     (IReclaim.Proof proof, int256 declaredValueMc, uint64 declaredTimestamp)
 */

import {ReclaimClient} from "@reclaimprotocol/zk-fetch";
import {transformForOnchain, verifyProof} from "@reclaimprotocol/js-sdk";
import {type Hex, encodeAbiParameters, parseAbiParameters, recoverMessageAddress} from "viem";

import {NWS_REQUEST_HEADERS} from "./nwsClient.js";

/** Mirror of IReclaim.ClaimInfo (Solidity). */
export interface ClaimInfo {
    provider: string;
    parameters: string;
    context: string;
}

/** Mirror of IReclaim.CompleteClaimData (Solidity). */
export interface CompleteClaimData {
    identifier: Hex;
    owner: Hex;
    timestampS: number;
    epoch: number;
}

/** Mirror of IReclaim.SignedClaim (Solidity). */
export interface SignedClaim {
    claim: CompleteClaimData;
    signatures: Hex[];
}

/** Mirror of IReclaim.Proof (Solidity). */
export interface OnchainProof {
    claimInfo: ClaimInfo;
    signedClaim: SignedClaim;
}

export interface ReclaimConfig {
    appId: string;
    appSecret: string;
}

export interface BuildSubmissionInput {
    config: ReclaimConfig;
    url: string;
    /** Pre-validated, already in milliCelsius (see nwsClient). */
    declaredValueMc: number;
    /** Pre-validated, already a unix-seconds integer (see nwsClient). */
    declaredTimestampSeconds: number;
}

export interface BuildSubmissionResult {
    onchainProof: OnchainProof;
    /** ABI-encoded blob ready to pass to `submitMeasurement(bytes)`. */
    encodedSubmission: Hex;
    /**
     * Witness EOAs that signed the proof, recovered from `signedClaim.signatures`.
     * Surfaced for diagnostic logging — if the on-chain `submitMeasurement` reverts
     * with `InvalidProof()`, cross-check these against the verifier's whitelisted
     * witnesses for the claim's epoch:
     *   `cast call $VERIFIER "fetchEpoch(uint32)(...)" $epoch --rpc-url $RPC`
     */
    recoveredSigners: Hex[];
}

/** Pre-parsed ABI shape used to encode the submission payload. */
const SUBMISSION_ABI_PARAMS = parseAbiParameters([
    "((string provider, string parameters, string context) claimInfo,",
    " ((bytes32 identifier, address owner, uint32 timestampS, uint32 epoch) claim, bytes[] signatures) signedClaim) proof,",
    "int256 declaredValueMc,",
    "uint64 declaredTimestamp",
].join(" "));

/**
 * Generate a zkProof for `url`, verify it locally, and produce both the on-chain
 * proof struct and the ABI-encoded submission blob.
 */
export async function buildSubmission(input: BuildSubmissionInput): Promise<BuildSubmissionResult> {
    const client = new ReclaimClient(input.config.appId, input.config.appSecret);

    const publicOptions = {
        method: "GET",
        headers: {...NWS_REQUEST_HEADERS},
    };

    // Reveal only the two JSON fields the on-chain contract cares about. Everything
    // else in the NWS response stays redacted by the zk-fetch attestor.
    const privateOptions = {
        responseRedactions: [
            {jsonPath: "$.properties.temperature.value"},
            {jsonPath: "$.properties.timestamp"},
        ],
    };

    const rawProof = await client.zkFetch(input.url, publicOptions, privateOptions);
    if (rawProof === undefined || rawProof === null) {
        throw new ReclaimError("zkfetch_returned_null", "zkFetch returned no proof", {url: input.url});
    }

    // zkFetch may return a single Proof or an array of Proof (one per chunk). For the
    // POC we expect a single chunk on the NWS observations endpoint; if the API
    // unexpectedly returns multiple, we keep the first and log it (see callers).
    const singleProof = Array.isArray(rawProof) ? rawProof[0] : rawProof;
    if (singleProof === undefined) {
        throw new ReclaimError("zkfetch_returned_null", "zkFetch returned an empty proof array", {url: input.url});
    }

    // Local sanity check on the witness signatures. The current js-sdk version
    // checks signature recovery only and does NOT re-fetch the upstream URL — which
    // is what we want (we already have the body via zkFetch and NWS rate-limits).
    const isVerified = await verifyProof(singleProof);
    if (!isVerified) {
        throw new ReclaimError("proof_local_verification_failed", "Reclaim proof failed local verifyProof()", {
            url: input.url,
        });
    }

    const {claimInfo, signedClaim} = transformForOnchain(singleProof);
    const onchainProof = toOnchainProof(claimInfo, signedClaim);

    if (input.declaredValueMc < Number.MIN_SAFE_INTEGER || input.declaredValueMc > Number.MAX_SAFE_INTEGER) {
        throw new ReclaimError("value_out_of_safe_range", "declaredValueMc not representable as JS number", {
            value: input.declaredValueMc,
        });
    }

    const recoveredSigners = await recoverProofSigners(onchainProof);

    const encodedSubmission = encodeAbiParameters(SUBMISSION_ABI_PARAMS, [
        onchainProof,
        BigInt(input.declaredValueMc),
        BigInt(input.declaredTimestampSeconds),
    ]);

    return {onchainProof, encodedSubmission, recoveredSigners};
}

/**
 * Reproduce the canonical serialisation that Reclaim's on-chain verifier expects
 * (`Claims.sol::serialise` + `verifySignature` in reclaimprotocol/reclaim-solidity-sdk)
 * and recover each signer EOA. Lets the keeper log who actually signed a proof, so
 * any mismatch against the verifier's whitelisted witness set is diagnosable in one
 * grep.
 *
 * Canonical message format (Solidity StringUtils):
 *   "{lowercase 0x-prefixed identifier hex}\n{lowercase 0x-prefixed owner hex}\n{timestampS}\n{epoch}"
 *
 * `recoverMessageAddress` adds the `\x19Ethereum Signed Message:\n{len}` prefix
 * automatically — matching `verifySignature`.
 */
async function recoverProofSigners(proof: OnchainProof): Promise<Hex[]> {
    const c = proof.signedClaim.claim;
    const message = [c.identifier.toLowerCase(), c.owner.toLowerCase(), String(c.timestampS), String(c.epoch)].join(
        "\n",
    );
    const signers: Hex[] = [];
    for (const sig of proof.signedClaim.signatures) {
        try {
            const addr = await recoverMessageAddress({message, signature: sig});
            signers.push(addr);
        } catch (err) {
            signers.push(`0xRECOVER_FAILED:${err instanceof Error ? err.message : String(err)}` as Hex);
        }
    }
    return signers;
}

export type ReclaimRejectionReason =
    | "zkfetch_returned_null"
    | "proof_local_verification_failed"
    | "value_out_of_safe_range";

export class ReclaimError extends Error {
    constructor(
        public readonly reason: ReclaimRejectionReason,
        message: string,
        public readonly context: Record<string, unknown> = {},
    ) {
        super(message);
        this.name = "ReclaimError";
    }
}

/**
 * Coerce the loosely-typed objects returned by `transformForOnchain` into the strict
 * OnchainProof shape. `transformForOnchain` is sound at runtime but its TS types are
 * `unknown`-ish in current SDK releases.
 */
function toOnchainProof(claimInfo: unknown, signedClaim: unknown): OnchainProof {
    if (!isObject(claimInfo) || !isObject(signedClaim)) {
        throw new ReclaimError("zkfetch_returned_null", "transformForOnchain returned non-object parts", {});
    }

    const claim = (signedClaim as Record<string, unknown>)["claim"];
    const sigs = (signedClaim as Record<string, unknown>)["signatures"];
    if (!isObject(claim) || !Array.isArray(sigs)) {
        throw new ReclaimError("zkfetch_returned_null", "signedClaim shape unexpected", {});
    }

    return {
        claimInfo: {
            provider: String((claimInfo as Record<string, unknown>)["provider"] ?? ""),
            parameters: String((claimInfo as Record<string, unknown>)["parameters"] ?? ""),
            context: String((claimInfo as Record<string, unknown>)["context"] ?? ""),
        },
        signedClaim: {
            claim: {
                identifier: (claim as Record<string, unknown>)["identifier"] as Hex,
                owner: (claim as Record<string, unknown>)["owner"] as Hex,
                timestampS: Number((claim as Record<string, unknown>)["timestampS"] ?? 0),
                epoch: Number((claim as Record<string, unknown>)["epoch"] ?? 0),
            },
            signatures: sigs.map((s) => s as Hex),
        },
    };
}

function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
