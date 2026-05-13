"use client";

import { useEffect, useState } from "react";

import { formatCountdown } from "@/lib/format";

interface Props {
  targetUnix: bigint;
  labels: { expired: string; remaining: string };
}

/**
 * Live countdown to a unix timestamp. Updates every second on the client.
 * Server-rendered fallback: shows the static countdown computed at SSR time.
 *
 * Labels are passed as a prop so the server parent can localize them.
 */
export function CountdownTimer({ targetUnix, labels }: Props) {
  const [now, setNow] = useState<number>(Math.floor(Date.now() / 1000));

  useEffect(() => {
    const id = setInterval(() => {
      setNow(Math.floor(Date.now() / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const remaining = Number(targetUnix) - now;

  if (remaining <= 0) {
    return <span className="font-mono text-muted">{labels.expired}</span>;
  }

  return (
    <span className="font-mono">
      {formatCountdown(targetUnix, now)} {labels.remaining}
    </span>
  );
}
