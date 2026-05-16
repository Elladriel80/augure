/**
 * On-chain submission of an encoded Reclaim proof to ReclaimWeatherSource.
 *
 * Uses viem 2.x (same major as dashboard/) with the explicit account/walletClient
 * pattern. The keeper signs locally with KEEPER_PRIVATE_KEY (testnet only; mainnet
 * must move to HSM / multisig / KMS — see POC-NOTES.md).
 *
 * The ABI is intentionally narrow: only what the keeper calls and the one event it
 * watches for. Full ABI is recoverable from `oracle-poc/contracts/out/` if needed.
 */

import {
    type Address,
    type Hash,
    type Hex,
    type PublicClient,
    type WalletClient,
    createPublicClient,
    createWalletClient,
    decodeEventLog,
    http,
} from "viem";
import {privateKeyToAccount} from "viem/accounts";
import {arbitrumSepolia} from "viem/chains";

export const RECLAIM_WEATHER_SOURCE_ABI = [
    {
        type: "function",
        name: "submitMeasurement",
        stateMutability: "nonpayable",
        inputs: [{name: "encodedSubmission", type: "bytes"}],
        outputs: [],
    },
    {
        type: "event",
        name: "MeasurementSubmitted",
        inputs: [
            {name: "location", type: "bytes32", indexed: true},
            {name: "measurementType", type: "bytes32", indexed: true},
            {name: "value", type: "int256", indexed: false},
            {name: "timestamp", type: "uint64", indexed: false},
            {name: "submitter", type: "address", indexed: true},
        ],
        anonymous: false,
    },
] as const;

export interface ChainSubmitterConfig {
    rpcUrl: string;
    contractAddress: Address;
    keeperPrivateKey: Hex;
}

export interface SubmittedMeasurement {
    txHash: Hash;
    blockNumber: bigint;
    gasUsed: bigint;
    location: Hex;
    measurementType: Hex;
    value: bigint;
    timestamp: bigint;
    submitter: Address;
}

export class ChainSubmitter {
    readonly publicClient: PublicClient;
    readonly walletClient: WalletClient;
    readonly contractAddress: Address;
    readonly account: ReturnType<typeof privateKeyToAccount>;

    constructor(config: ChainSubmitterConfig) {
        this.account = privateKeyToAccount(config.keeperPrivateKey);
        this.contractAddress = config.contractAddress;

        const transport = http(config.rpcUrl);
        this.publicClient = createPublicClient({chain: arbitrumSepolia, transport});
        this.walletClient = createWalletClient({account: this.account, chain: arbitrumSepolia, transport});
    }

    /**
     * Submit an encoded measurement and wait for inclusion. Returns the parsed
     * MeasurementSubmitted event from the receipt, or throws if the tx reverted
     * or the event is missing.
     */
    async submit(encodedSubmission: Hex): Promise<SubmittedMeasurement> {
        const txHash = await this.walletClient.writeContract({
            account: this.account,
            chain: arbitrumSepolia,
            address: this.contractAddress,
            abi: RECLAIM_WEATHER_SOURCE_ABI,
            functionName: "submitMeasurement",
            args: [encodedSubmission],
        });

        const receipt = await this.publicClient.waitForTransactionReceipt({hash: txHash});
        if (receipt.status !== "success") {
            throw new ChainSubmitError("tx_reverted", `Transaction ${txHash} reverted`, {txHash});
        }

        const event = parseMeasurementSubmittedEvent(receipt.logs, this.contractAddress);
        if (!event) {
            throw new ChainSubmitError(
                "event_missing",
                `Transaction ${txHash} succeeded but emitted no MeasurementSubmitted event from ${this.contractAddress}`,
                {txHash, logsCount: receipt.logs.length},
            );
        }

        return {
            txHash,
            blockNumber: receipt.blockNumber,
            gasUsed: receipt.gasUsed,
            ...event,
        };
    }
}

export type ChainSubmitRejectionReason = "tx_reverted" | "event_missing";

export class ChainSubmitError extends Error {
    constructor(
        public readonly reason: ChainSubmitRejectionReason,
        message: string,
        public readonly context: Record<string, unknown> = {},
    ) {
        super(message);
        this.name = "ChainSubmitError";
    }
}

interface ParsedEvent {
    location: Hex;
    measurementType: Hex;
    value: bigint;
    timestamp: bigint;
    submitter: Address;
}

function parseMeasurementSubmittedEvent(
    logs: readonly {address: Address; topics: readonly Hex[]; data: Hex}[],
    contractAddress: Address,
): ParsedEvent | null {
    const targetAddress = contractAddress.toLowerCase();
    for (const log of logs) {
        if (log.address.toLowerCase() !== targetAddress) continue;
        try {
            const decoded = decodeEventLog({
                abi: RECLAIM_WEATHER_SOURCE_ABI,
                topics: [...log.topics] as [Hex, ...Hex[]],
                data: log.data,
            });
            if (decoded.eventName !== "MeasurementSubmitted") continue;
            const args = decoded.args as {
                location: Hex;
                measurementType: Hex;
                value: bigint;
                timestamp: bigint;
                submitter: Address;
            };
            return {
                location: args.location,
                measurementType: args.measurementType,
                value: args.value,
                timestamp: args.timestamp,
                submitter: args.submitter,
            };
        } catch {
            // Not a MeasurementSubmitted log — skip silently, the keeper logs the
            // missing-event case once at the end if no match was found.
            continue;
        }
    }
    return null;
}
