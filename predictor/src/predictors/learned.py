"""LearnedPredictor — live inference for the sklearn LR L2 model trained in
runs_learning/.

This predictor reconstructs the trained model in-memory from the run.json
written by `scripts/train_learned.py` (schema v2+). No pickling: we replay
the exact closed-form formula

    p_yes = sigmoid(intercept + Σ coef_i · (x_i − mean_i) / std_i)

where `coef_i`, `mean_i`, `std_i` and `intercept` are serialised in run.json
and `x_i` is the feature value computed at inference time on the live
ContractSpec via the shared extractors in `src.learning.features`.

The predictor composes the existing sub-predictors (climatology,
forecast_blend, ensemble) to materialise a record dict that matches the
forward_*.json schema, then runs the feature extractors against it. This
guarantees train-time and inference-time features stay consistent — same
code path on both sides.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from src.weather import OpenMeteoClient
from src.learning.features import FEATURE_SETS, extract
from .base import ContractSpec, Prediction, Predictor
from .climatology import ClimatologyPredictor
from .forecast_blend import ForecastBlendPredictor
from .ensemble import EnsemblePredictor


REQUIRED_SCHEMA_VERSION = 2


def _find_latest_run_json(runs_root: Path) -> Path:
    """Return the most recent runs_learning/<ts>/run.json by timestamp folder name."""
    candidates = sorted(runs_root.glob("*/run.json"))
    if not candidates:
        raise FileNotFoundError(
            f"No run.json under {runs_root}. Train a learned model first via "
            f"`python predictor/scripts/train_learned.py --feature-set v2`."
        )
    return candidates[-1]


def _sigmoid(z: float) -> float:
    # Guard against overflow on extreme logits.
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


class LearnedPredictor(Predictor):
    """Sklearn LR L2 over named features. Live inference, no refit."""

    name = "learned"

    def __init__(
        self,
        weather_client: Optional[OpenMeteoClient] = None,
        run_json_path: Optional[Path] = None,
        runs_root: Optional[Path] = None,
        sub_climato: Optional[ClimatologyPredictor] = None,
        sub_forecast_blend: Optional[ForecastBlendPredictor] = None,
        sub_ensemble: Optional[EnsemblePredictor] = None,
    ):
        # Resolve run.json path: explicit > auto-discover under runs_root > project default.
        if run_json_path is None:
            if runs_root is None:
                # Project default: <repo>/predictor/runs_learning
                from src.config import DATA_DIR  # type: ignore
                runs_root = DATA_DIR.parent / "runs_learning"
            run_json_path = _find_latest_run_json(Path(runs_root))
        run_json_path = Path(run_json_path)

        record = json.loads(run_json_path.read_text(encoding="utf-8"))
        schema = int(record.get("schema_version", 1))
        if schema < REQUIRED_SCHEMA_VERSION:
            raise ValueError(
                f"run.json at {run_json_path} has schema_version={schema}, "
                f"need >= {REQUIRED_SCHEMA_VERSION}. Re-run train_learned.py to "
                f"regenerate with full inference fields (intercept, feature_means, "
                f"feature_stds)."
            )

        # Required model state
        try:
            self.feature_names: list[str] = record["feature_names"]
            self.intercept: float = float(record["intercept"])
            self.coefs: dict[str, float] = {
                k: float(v) for k, v in record["feature_importances"].items()
            }
            self.means: dict[str, float] = {
                k: float(v) for k, v in record["feature_means"].items()
            }
            self.stds: dict[str, float] = {
                k: float(v) for k, v in record["feature_stds"].items()
            }
            self.feature_set_used: str = record["feature_set_used"]
        except KeyError as e:
            raise ValueError(
                f"run.json at {run_json_path} missing required field {e}. "
                "Regenerate via train_learned.py."
            ) from e

        if self.feature_set_used not in FEATURE_SETS:
            raise ValueError(
                f"Unknown feature_set '{self.feature_set_used}'. Known: "
                f"{sorted(FEATURE_SETS.keys())}"
            )
        self.feature_spec = FEATURE_SETS[self.feature_set_used]
        self.trained_at: str = record.get("timestamp_utc", "unknown")
        self.run_json_path = run_json_path

        # Expose a richer name (e.g. "learned_v2") so multi-model reports stay legible.
        self.name = f"learned_{self.feature_set_used}"

        # Sub-predictors. Reusable — caller can inject mocks for tests or share
        # a single OpenMeteoClient across all three to dedupe cache hits.
        self.weather = weather_client or OpenMeteoClient()
        self.climato = sub_climato or ClimatologyPredictor(self.weather)
        self.forecast_blend = sub_forecast_blend or ForecastBlendPredictor(self.weather)
        self.ensemble = sub_ensemble or EnsemblePredictor(self.weather)

    def predict(self, contract: ContractSpec) -> Prediction:
        # 1. Materialise sub-predictions (same code path as forward_predict.py).
        clim_pred = self.climato.predict(contract)
        fb_pred = self.forecast_blend.predict(contract)
        ens_pred = self.ensemble.predict(contract)

        # 2. Build a record dict matching the forward_*.json shape that the
        #    feature extractors expect. The keys here mirror what forward_predict
        #    writes per market, so we can call `extract()` unchanged.
        record = {
            "location_key": contract.location_key,
            "target_date": contract.target_date.isoformat(),
            "variable": contract.variable,
            "lower": contract.lower,
            "upper": contract.upper,
            "predictions": {
                "climatology": {
                    "prob_yes": clim_pred.prob_yes,
                    "inputs": clim_pred.inputs,
                },
                "forecast_blend": {
                    "prob_yes": fb_pred.prob_yes,
                    "inputs": fb_pred.inputs,
                },
                "ensemble": {
                    "prob_yes": ens_pred.prob_yes,
                    "inputs": ens_pred.inputs,
                },
            },
        }

        # 3. Extract features (same FEATURE_SETS[set] as training).
        feats = extract(record, self.feature_spec)
        if feats is None:
            # One or more features came back None — typically a missing geo entry
            # in stations.json or an out-of-horizon forecast. Fall back to the
            # climatology prior rather than guess. The Prediction.method field
            # signals the degradation so downstream reports can flag it.
            missing = [
                name for name, fn in self.feature_spec if fn(record) is None
            ]
            return Prediction(
                contract=contract,
                prob_yes=clim_pred.prob_yes,
                method=f"{self.name}[fallback_climato]",
                inputs={
                    "reason": "feature_extraction_returned_none",
                    "missing_features": missing,
                    "feature_set": self.feature_set_used,
                    "trained_at": self.trained_at,
                    "sub_p_climatology": clim_pred.prob_yes,
                    "sub_p_forecast_blend": fb_pred.prob_yes,
                    "sub_p_ensemble": ens_pred.prob_yes,
                },
                confidence=clim_pred.confidence,
            )

        # 4. Z-score using the means/stds frozen at training time.
        z = {}
        for name in self.feature_names:
            mu = self.means[name]
            sigma = self.stds[name]
            # Guard against degenerate scaler stds (column was constant in training).
            denom = sigma if sigma > 1e-9 else 1.0
            z[name] = (feats[name] - mu) / denom

        # 5. Apply the closed-form LR: logit = intercept + Σ coef · z.
        logit = self.intercept + sum(
            self.coefs[name] * z[name] for name in self.feature_names
        )
        p_yes = _sigmoid(logit)
        # Numerical clamp — sigmoid is mathematically in (0,1) but report a clean range.
        p_yes = max(0.0, min(1.0, p_yes))

        return Prediction(
            contract=contract,
            prob_yes=p_yes,
            method=self.name,
            inputs={
                "feature_set": self.feature_set_used,
                "trained_at": self.trained_at,
                "run_json_path": str(self.run_json_path),
                "raw_features": feats,
                "z_scored": z,
                "logit": logit,
                "intercept": self.intercept,
                "sub_p_climatology": clim_pred.prob_yes,
                "sub_p_forecast_blend": fb_pred.prob_yes,
                "sub_p_ensemble": ens_pred.prob_yes,
            },
            confidence=ens_pred.confidence,
        )
