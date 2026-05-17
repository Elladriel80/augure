/**
 * Keeper entry point.
 *
 * Poll loop: NWS → zkFetch → on-chain. Intentionally simple: no retry queue, no
 * exponential backoff, no metrics push. A failed iteration logs and the next tick
 * tries again. POC, not production.
 *
 * SIGTERM / SIGINT trigger a graceful shutdown — the loop stops sleeping, finishes
 * the current iteration if one is mid-flight, then exits 0.
 */

import {config as loadDotenv} from "dotenv";
import {type Address, type Hex, getAddress, isAddress, isHex} from "viem";

import {ChainSubmitter} from "./chainSubmit.js";
import {NwsRejection, fetchLatestObservation} from "./nwsClient.js";
import {ReclaimError, buildSubmission} from "./reclaimProof.js";

loadDotenv();

interface KeeperConfig {
    reclaimAppId: string;
    reclaimAppSecret: string;
    rpcUrl: string;
    contractAddress: Address;
    keeperPrivateKey: Hex;
    nwsStationId: string;
    nwsBaseUrl: string;
    pollIntervalSeconds: number;
}

function loadConfig(): KeeperConfig {
    const get = (key: string): string => {
        const v = process.env[key];
        if (v === undefined || v === "") throw new Error(`Missing required env var: ${key}`);
        return v;
    };

    const contractRaw = get("RECLAIM_WEATHER_SOURCE_ADDRESS");
    if (!isAddress(contractRaw)) throw new Error(`RECLAIM_WEATHER_SOURCE_ADDRESS is not a valid address: ${contractRaw}`);

    const keyRaw = get("KEEPER_PRIVATE_KEY");
    if (!isHex(keyRaw) || keyRaw.length !== 66) {
        throw new Error("KEEPER_PRIVATE_KEY must be 0x-prefixed 32-byte hex");
    }

    const intervalRaw = process.env["POLL_INTERVAL_SECONDS"] ?? "600";
    const interval = Number.parseInt(intervalRaw, 10);
    if (!Number.isFinite(interval) || interval < 30) {
        throw new Error(`POLL_INTERVAL_SECONDS must be >= 30, got "${intervalRaw}"`);
    }

    return {
        reclaimAppId: get("RECLAIM_APP_ID"),
        reclaimAppSecret: get("RECLAIM_APP_SECRET"),
        rpcUrl: get("ARBITRUM_SEPOLIA_RPC"),
        contractAddress: getAddress(contractRaw),
        keeperPrivateKey: keyRaw,
        nwsStationId: process.env["NWS_STATION_ID"] ?? "KJFK",
        nwsBaseUrl: process.env["NWS_BASE_URL"] ?? "https://api.weather.gov",
        pollIntervalSeconds: interval,
    };
}

/** Minimal structured logger — single-line JSON per event. No external deps. */
function logEvent(level: "info" | "warn" | "error", event: string, fields: Record<string, unknown> = {}): void {
    const line = JSON.stringify({
        ts: new Date().toISOString(),
        level,
        event,
        ...fields,
    });
    if (level === "error") {
        process.stderr.write(line + "\n");
    } else {
        process.stdout.write(line + "\n");
    }
}

interface ShutdownState {
    requested: boolean;
}

async function runIteration(config: KeeperConfig, submitter: ChainSubmitter): Promise<void> {
    logEvent("info", "iteration_start", {stationId: config.nwsStationId});

    let observation;
    try {
        observation = await fetchLatestObservation({baseUrl: config.nwsBaseUrl, stationId: config.nwsStationId});
    } catch (err) {
        if (err instanceof NwsRejection) {
            logEvent("warn", "nws_rejected", {reason: err.reason, message: err.message, ...err.context});
            return;
        }
        throw err;
    }

    logEvent("info", "nws_observation", {
        url: observation.url,
        temperatureMilliCelsius: observation.temperatureMilliCelsius,
        timestampUnixSeconds: observation.timestampUnixSeconds,
    });

    let submission;
    try {
        submission = await buildSubmission({
            config: {appId: config.reclaimAppId, appSecret: config.reclaimAppSecret},
            url: observation.url,
            declaredValueMc: observation.temperatureMilliCelsius,
            declaredTimestampSeconds: observation.timestampUnixSeconds,
        });
    } catch (err) {
        if (err instanceof ReclaimError) {
            logEvent("warn", "reclaim_rejected", {reason: err.reason, message: err.message, ...err.context});
            return;
        }
        throw err;
    }

    const claim = submission.onchainProof.signedClaim.claim;
    logEvent("info", "proof_built", {
        encodedBytes: (submission.encodedSubmission.length - 2) / 2,
        // Diagnostic fields — if the verifier rejects a proof at submit time, the
        // recovered signers can be cross-checked against the verifier's whitelisted
        // witnesses for this epoch:
        //   cast call $VERIFIER "fetchEpoch(uint32)(...)" $epoch --rpc-url $RPC
        epoch: claim.epoch,
        signers: submission.recoveredSigners,
    });

    try {
        const result = await submitter.submit(submission.encodedSubmission);
        logEvent("info", "measurement_submitted", {
            txHash: result.txHash,
            blockNumber: result.blockNumber.toString(),
            gasUsed: result.gasUsed.toString(),
            value: result.value.toString(),
            timestamp: result.timestamp.toString(),
            submitter: result.submitter,
        });
    } catch (err) {
        // On revert (e.g. InvalidProof()), surface the diagnostic fields again at error
        // level so a single grep on level=error gives the full mismatch picture.
        const message = err instanceof Error ? err.message : String(err);
        logEvent("error", "submit_failed", {
            message,
            epoch: claim.epoch,
            signers: submission.recoveredSigners,
        });
        throw err;
    }
}

async function sleepInterruptible(seconds: number, shutdown: ShutdownState): Promise<void> {
    const intervalMs = 1000;
    const totalTicks = seconds;
    for (let i = 0; i < totalTicks; i++) {
        if (shutdown.requested) return;
        await new Promise<void>((resolve) => setTimeout(resolve, intervalMs));
    }
}

async function main(): Promise<void> {
    const config = loadConfig();
    const submitter = new ChainSubmitter({
        rpcUrl: config.rpcUrl,
        contractAddress: config.contractAddress,
        keeperPrivateKey: config.keeperPrivateKey,
    });

    logEvent("info", "keeper_start", {
        contractAddress: config.contractAddress,
        keeperAddress: submitter.account.address,
        stationId: config.nwsStationId,
        pollIntervalSeconds: config.pollIntervalSeconds,
    });

    const shutdown: ShutdownState = {requested: false};
    const requestShutdown = (signal: NodeJS.Signals): void => {
        if (shutdown.requested) return;
        shutdown.requested = true;
        logEvent("info", "shutdown_requested", {signal});
    };
    process.on("SIGTERM", () => requestShutdown("SIGTERM"));
    process.on("SIGINT", () => requestShutdown("SIGINT"));

    while (!shutdown.requested) {
        try {
            await runIteration(config, submitter);
        } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            const stack = err instanceof Error ? err.stack : undefined;
            logEvent("error", "iteration_failed", {message, stack});
        }
        if (shutdown.requested) break;
        await sleepInterruptible(config.pollIntervalSeconds, shutdown);
    }

    logEvent("info", "keeper_stopped", {});
}

main().catch((err) => {
    const message = err instanceof Error ? err.message : String(err);
    logEvent("error", "keeper_fatal", {message});
    process.exit(1);
});
