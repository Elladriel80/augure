"""Ledger CSV pour les paris simulés : ouverture + résolution + scoring."""
from __future__ import annotations
import csv
from dataclasses import dataclass, asdict, fields
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

from src.config import LEDGER_DIR


@dataclass
class PaperBet:
    """Un pari simulé. Une ligne par pari placé."""
    bet_id: str                     # unique
    placed_at_utc: str              # ISO
    market_ticker: str
    event_ticker: str
    target_date: str                # ISO (jour de résolution)
    side: str                       # "YES" ou "NO"
    stake_usd: float                # mise en USD
    entry_price: float              # prix YES au moment du pari (∈ [0, 1])
    prob_model: float               # P(OUI) selon le modèle
    prob_market_implied: float      # P(OUI) implicite par le marché à l'entrée
    edge: float                     # prob_model - prob_market_implied
    method: str                     # nom du predictor
    spec: str                       # description normalisée
    # Résolution (vides au moment de l'ouverture)
    resolved_at_utc: Optional[str] = None
    resolution: Optional[str] = None     # "yes", "no", "void"
    pnl_usd: Optional[float] = None      # gain/perte simulé en USD


class Ledger:
    """Persistance CSV append-only du ledger de paris."""

    DEFAULT_PATH = LEDGER_DIR / "paper_bets.csv"

    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._field_names = [f.name for f in fields(PaperBet)]
        if not self.path.exists():
            self._write_header()

    def _write_header(self):
        with self.path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self._field_names)

    def append(self, bet: PaperBet) -> None:
        with self.path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self._field_names)
            writer.writerow(asdict(bet))

    def read_all(self) -> list[PaperBet]:
        if not self.path.exists():
            return []
        out = []
        with self.path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Cast types (CSV est tout-string)
                for k in ("stake_usd", "entry_price", "prob_model", "prob_market_implied", "edge"):
                    row[k] = float(row[k]) if row[k] not in (None, "") else None
                if row.get("pnl_usd") not in (None, ""):
                    row["pnl_usd"] = float(row["pnl_usd"])
                else:
                    row["pnl_usd"] = None
                if row.get("resolved_at_utc") == "":
                    row["resolved_at_utc"] = None
                if row.get("resolution") == "":
                    row["resolution"] = None
                out.append(PaperBet(**row))
        return out

    def write_all(self, bets: list[PaperBet]) -> None:
        """Écrit tout le ledger (utile après update des résolutions)."""
        with self.path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self._field_names)
            writer.writeheader()
            for bet in bets:
                writer.writerow(asdict(bet))


def make_bet_id() -> str:
    """ID basé timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
