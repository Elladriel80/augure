"""pytest bootstrap — make the predictor's scripts/ and src/ importable.

train_learned.py is a CLI script rather than an installed module, so we
extend sys.path here once for the whole test session.
"""
from __future__ import annotations

import sys
from pathlib import Path

PREDICTOR_ROOT = Path(__file__).resolve().parents[1]
for sub in ("scripts", ""):
    p = PREDICTOR_ROOT / sub if sub else PREDICTOR_ROOT
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
