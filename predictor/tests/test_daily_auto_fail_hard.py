"""Tests du contrat fail-hard de daily_auto.main().

Cf. AUDIT-PASSE-4 §P4-1 / §P4-6. Le risque adressé : un step interne lève
une exception silencieuse, daily_auto renvoyait 0, le workflow GitHub
``daily-trading.yml`` (qui a ``contents: write`` sur main) commitait quand
même l'état partiel. Un ledger corrompu pouvait être pushé sur main avec
une CI verte.

Contrat post-fix :
  - Une exception dans n'importe quel step est capturée et tracée.
  - main() renvoie 2 si au moins un step a levé.
  - Le happy path (aucune exception) renvoie toujours 0.
"""
from __future__ import annotations

import pytest

import daily_auto


def _silence_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mocke tous les steps en no-op qui renvoient un dict vide."""
    monkeypatch.setattr(daily_auto, "step_finalize", lambda: {})
    monkeypatch.setattr(daily_auto, "step_capture", lambda dry_run: {})
    monkeypatch.setattr(daily_auto, "step_manifest", lambda: {"ok": True})


def test_main_returns_0_on_happy_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _silence_steps(monkeypatch)
    monkeypatch.setattr("sys.argv", ["daily_auto.py", "--dry-run"])
    assert daily_auto.main() == 0


def test_main_returns_2_when_finalize_raises(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> dict:
        raise RuntimeError("ledger corrompu : bankroll dégradé")

    _silence_steps(monkeypatch)
    monkeypatch.setattr(daily_auto, "step_finalize", boom)
    monkeypatch.setattr("sys.argv", ["daily_auto.py", "--dry-run"])

    assert daily_auto.main() == 2
    captured = capsys.readouterr()
    # Le message custom du _run_step va sur stdout, le traceback sur stderr.
    assert "exception" in captured.out.lower()
    assert "ledger corrompu" in captured.err


def test_main_returns_2_when_capture_raises(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(dry_run: bool) -> dict:
        raise RuntimeError("capture explose")

    _silence_steps(monkeypatch)
    monkeypatch.setattr(daily_auto, "step_capture", boom)
    monkeypatch.setattr("sys.argv", ["daily_auto.py", "--dry-run"])

    assert daily_auto.main() == 2


def test_main_returns_2_when_manifest_raises(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> dict:
        raise RuntimeError("build_dashboard_manifest.py failed with rc=1")

    _silence_steps(monkeypatch)
    monkeypatch.setattr(daily_auto, "step_manifest", boom)
    # Mode non-dry-run pour activer step_manifest.
    monkeypatch.setattr("sys.argv", ["daily_auto.py"])

    assert daily_auto.main() == 2
    out = capsys.readouterr().out
    assert "manifest" in out.lower()


def test_main_skips_manifest_in_dry_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """En dry-run, step_manifest ne doit pas être appelé (pas de push)."""
    calls: list[str] = []

    def fake_manifest() -> dict:
        calls.append("manifest")
        return {"ok": True}

    _silence_steps(monkeypatch)
    monkeypatch.setattr(daily_auto, "step_manifest", fake_manifest)
    monkeypatch.setattr("sys.argv", ["daily_auto.py", "--dry-run"])

    assert daily_auto.main() == 0
    assert calls == []  # step_manifest pas appelé en dry-run
