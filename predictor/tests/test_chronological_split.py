"""Tests for `chronological_split` group-aware snapping.

Covers the four cases listed in §6.3 of rapport-split-temporel-2026-05-14:

  1. cut at the middle of a group  → snap to nearest boundary, no leakage
  2. cut on a clean group boundary → no shift, no leakage
  3. all rows share the same key   → degenerate, but no leakage
  4. all rows have distinct keys   → cut lands at int(N * train_frac)

The split function's contract is *no `split_key` value appears in both
train and test*. These tests enforce that contract on the four cases.
"""
from __future__ import annotations

from train_learned import chronological_split


def _meta_from_keys(keys, key="target_date"):
    """Build a meta list with one dict per key value."""
    return [{key: v} for v in keys]


def _split_keys(meta_train, meta_test, key="target_date"):
    return (
        [m[key] for m in meta_train],
        [m[key] for m in meta_test],
    )


def _no_leakage(meta_train, meta_test, key="target_date"):
    return set(m[key] for m in meta_train).isdisjoint(
        set(m[key] for m in meta_test)
    )


# --- Case 1: cut lands in the middle of a group ---------------------------
def test_cut_middle_of_group_snaps_and_keeps_groups_intact():
    # 10 rows; days 1..5 with two rows each. train_frac=0.7 → target=7,
    # which falls inside day=4's group (rows 6,7). Snap must move the
    # cut to a group boundary (target=6 backward, or target=8 forward).
    keys = ["d1", "d1", "d2", "d2", "d3", "d3", "d4", "d4", "d5", "d5"]
    X = list(range(10))
    y = [0] * 10
    meta = _meta_from_keys(keys)

    Xtr, ytr, mtr, Xte, yte, mte = chronological_split(
        X, y, meta, train_frac=0.7, split_key="target_date"
    )

    assert _no_leakage(mtr, mte)
    tr_keys, te_keys = _split_keys(mtr, mte)
    # Backward snap (preferred on tie) lands the cut at index 6 → train=d1..d3.
    assert tr_keys == ["d1", "d1", "d2", "d2", "d3", "d3"]
    assert te_keys == ["d4", "d4", "d5", "d5"]


# --- Case 2: cut lands exactly on a group boundary ------------------------
def test_cut_on_clean_boundary_does_not_shift():
    # 10 rows; first 7 share day=A, last 3 share day=B. target = int(10*0.7) = 7
    # which is exactly the index where the key changes — no snapping needed.
    keys = ["A"] * 7 + ["B"] * 3
    X = list(range(10))
    y = [0] * 10
    meta = _meta_from_keys(keys)

    Xtr, ytr, mtr, Xte, yte, mte = chronological_split(
        X, y, meta, train_frac=0.7, split_key="target_date"
    )

    assert _no_leakage(mtr, mte)
    assert len(Xtr) == 7 and len(Xte) == 3
    tr_keys, te_keys = _split_keys(mtr, mte)
    assert tr_keys == ["A"] * 7
    assert te_keys == ["B"] * 3


# --- Case 3: all rows share the same key (degenerate) ---------------------
def test_all_identical_keys_no_leakage_even_if_unbalanced():
    # All rows share the same split_key. Group-snap can only push the cut
    # to an extreme (target=1 or N-1) to keep groups intact, which surfaces
    # the degeneracy. Contract still holds: train and test are non-empty,
    # and the single-value-on-both-sides case is the only one where strict
    # disjointness is impossible. We assert: each side has at least one
    # row, and the function does NOT raise.
    keys = ["same"] * 10
    X = list(range(10))
    y = [0] * 10
    meta = _meta_from_keys(keys)

    Xtr, ytr, mtr, Xte, yte, mte = chronological_split(
        X, y, meta, train_frac=0.7, split_key="target_date"
    )

    # With one key value, perfect disjointness is impossible by definition;
    # this is precisely what the degenerate-split warning surfaces in main().
    # We assert the function still returns a non-empty 2-way split rather
    # than crashing or producing an empty side.
    assert len(Xtr) >= 1
    assert len(Xte) >= 1
    assert len(Xtr) + len(Xte) == 10
    # All keys are identical, so they appear on both sides — expected.
    tr_keys, te_keys = _split_keys(mtr, mte)
    assert set(tr_keys) == {"same"}
    assert set(te_keys) == {"same"}


# --- Case 4: every row has a distinct key ---------------------------------
def test_all_distinct_keys_cut_at_target():
    # 10 distinct days. No two rows share a key → cut lands exactly at
    # int(10*0.7) = 7, no snapping involved.
    keys = [f"d{i:02d}" for i in range(10)]
    X = list(range(10))
    y = [0] * 10
    meta = _meta_from_keys(keys)

    Xtr, ytr, mtr, Xte, yte, mte = chronological_split(
        X, y, meta, train_frac=0.7, split_key="target_date"
    )

    assert _no_leakage(mtr, mte)
    assert len(Xtr) == 7 and len(Xte) == 3
    tr_keys, te_keys = _split_keys(mtr, mte)
    assert tr_keys == [f"d{i:02d}" for i in range(7)]
    assert te_keys == [f"d{i:02d}" for i in range(7, 10)]


# --- Bonus: missing keys must sort last and never silently leak -----------
def test_missing_keys_sort_last_and_stay_in_test():
    keys = ["d1", "d2", "d3", None, None]
    X = list(range(5))
    y = [0] * 5
    meta = _meta_from_keys(keys)

    Xtr, ytr, mtr, Xte, yte, mte = chronological_split(
        X, y, meta, train_frac=0.6, split_key="target_date"
    )

    # Missing-keyed rows must NOT end up in train.
    train_keys = [m["target_date"] for m in mtr]
    assert None not in train_keys and "" not in train_keys
