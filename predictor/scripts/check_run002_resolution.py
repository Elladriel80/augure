"""Check resolution status of Run 002 event (KXLOWTNYC-26MAY11).

Pulls a fresh snapshot from Kalshi (regardless of status=open/settled) and prints
status + result + last quotes per bin. Exit 0 if at least one market is settled,
1 otherwise.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.kalshi import KalshiClient

EVENT_TICKER = "KXLOWTNYC-26MAY11"
OUR_BIN = "KXLOWTNYC-26MAY11-B50.5"


def main() -> int:
    c = KalshiClient()
    ev = c.get_event(EVENT_TICKER)
    snap_path = c.snapshot_event(ev)
    print(f">> Snapshot ecrit: {snap_path}")
    print(f">> Event: {ev.event_ticker} - {len(ev.markets)} markets\n")

    any_settled = False
    our_market = None
    for m in ev.markets:
        result = getattr(m, "result", None) or "-"
        status = m.status or "?"
        yb = m.yes_bid if m.yes_bid is not None else "-"
        ya = m.yes_ask if m.yes_ask is not None else "-"
        last = getattr(m, "last_price", None)
        last_str = f"{last}" if last is not None else "-"
        marker = "  <-- OURS" if m.ticker == OUR_BIN else ""
        print(f"  {m.ticker:32s} status={status:10s} result={result:6s} "
              f"yes_bid={yb}  yes_ask={ya}  last={last_str}{marker}")
        if status == "settled" or (result and result != "-"):
            any_settled = True
            if m.ticker == OUR_BIN:
                our_market = m

    print()
    if not any_settled:
        print(">> Aucun marche settled. Le NWS daily climate report n'est pas encore sorti.")
        print(">> Resolution attendue ~11-13h UTC le 12 mai. Relance ce script plus tard.")
        return 1

    print(">> AU MOINS UN MARCHE SETTLED.")
    if our_market is not None:
        r = (getattr(our_market, "result", None) or "").lower()
        if r == "yes":
            print(f">> Bin B50.5 (le notre, side NO) => YES. NO a perdu.")
            print(f"   P&L paper: -$100 (stake total) sur ~156 contrats NO @ 64c.")
        elif r == "no":
            print(f">> Bin B50.5 (le notre, side NO) => NO. NO a gagne.")
            print(f"   P&L paper: +$56.25 (156 contrats * $0.36 gagnes).")
        else:
            print(f">> Bin B50.5 result='{r}' (ni yes ni no?)")
    else:
        print(">> Bin B50.5 pas encore settled mais d'autres bins le sont.")

    # Cherche le bin "yes" pour deviner la low observee
    print("\n>> Bin gagnant (result=yes):")
    for m in ev.markets:
        r = (getattr(m, "result", None) or "").lower()
        if r == "yes":
            print(f"   {m.ticker} - {m.title if hasattr(m, 'title') else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
