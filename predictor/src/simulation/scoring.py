"""Métriques de scoring : accuracy, Brier score, log loss."""
from __future__ import annotations
import math


def brier_score(prob_yes: float, outcome: int) -> float:
    """Brier score = (proba - outcome)². Plus bas = meilleur. Range [0, 1]."""
    return (prob_yes - outcome) ** 2


def log_loss(prob_yes: float, outcome: int, eps: float = 1e-9) -> float:
    """Log loss = -[y*log(p) + (1-y)*log(1-p)]. Plus bas = meilleur."""
    p = max(eps, min(1 - eps, prob_yes))
    return -(outcome * math.log(p) + (1 - outcome) * math.log(1 - p))


def aggregate_metrics(records: list[dict]) -> dict:
    """Calcule métriques agrégées sur une liste de prédictions résolues.

    Chaque record doit avoir: {'prob_yes': float, 'outcome': 0 or 1}
    """
    if not records:
        return {"n": 0}

    n = len(records)
    n_yes = sum(r["outcome"] for r in records)

    brier = sum(brier_score(r["prob_yes"], r["outcome"]) for r in records) / n
    ll = sum(log_loss(r["prob_yes"], r["outcome"]) for r in records) / n

    # Brier de référence : prédire P=base_rate constant
    base_rate = n_yes / n
    brier_baseline = sum(brier_score(base_rate, r["outcome"]) for r in records) / n

    # Accuracy avec seuil 0.5
    correct = sum(1 for r in records if (r["prob_yes"] >= 0.5) == (r["outcome"] == 1))
    accuracy = correct / n

    return {
        "n": n,
        "base_rate": base_rate,
        "accuracy_at_0.5": accuracy,
        "brier_score": brier,
        "brier_baseline_constant": brier_baseline,
        "brier_skill_score": 1 - (brier / brier_baseline) if brier_baseline > 0 else 0,
        "log_loss": ll,
    }


def event_top1_accuracy(event_groups: list[list[dict]]) -> dict:
    """Pour chaque event (groupe de bins mutuellement exclusifs), vérifie si
    la prédiction top-1 (bin le plus probable) correspond au bin résolu OUI.
    """
    if not event_groups:
        return {"n_events": 0}

    n_correct = 0
    n_events = 0
    for markets in event_groups:
        if not markets:
            continue
        # Au plus un market résolu YES par event mutuellement exclusif
        winners = [m for m in markets if m["outcome"] == 1]
        if not winners:
            continue
        n_events += 1
        # Top-1 prédit
        top = max(markets, key=lambda m: m["prob_yes"])
        if top["outcome"] == 1:
            n_correct += 1

    return {
        "n_events": n_events,
        "top1_correct": n_correct,
        "top1_accuracy": n_correct / n_events if n_events > 0 else 0,
    }
