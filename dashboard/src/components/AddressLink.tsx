import { explorerAddressUrl } from "@/lib/chain";
import { shortAddress } from "@/lib/format";

interface Props {
  address: string;
  /** Render the full address instead of the short form. */
  full?: boolean;
}

export function AddressLink({ address, full = false }: Props) {
  return (
    <a
      href={explorerAddressUrl(address)}
      target="_blank"
      rel="noreferrer noopener"
      className="font-mono text-accent hover:underline break-all"
      title={address}
    >
      {full ? address : shortAddress(address)}
    </a>
  );
}
