"""Learned predictor — our own model trained on Kalshi resolution history.

Phase A.3 of the predictor work. Built after the meta-ensemble of vendor
forecasts (ECMWF + GraphCast + GFS + JMA averaged) was decisively
outperformed by Kalshi mid on N=138 resolved markets (2026-05-11 bench).

The bet: a model that takes those vendor forecasts as features (among
others) and learns weights from outcomes can extract signal that pure
averaging cannot. Frugal stack — sklearn logistic regression with L2,
explicit feature importance tracking, iterative feature engineering.
"""
