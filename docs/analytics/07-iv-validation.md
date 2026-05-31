# Lecture 7 — IV & Greek Validation

## Why Validate?

An implied-volatility solver is only useful if it agrees with the
exchange's own pricing engine. Small numerical differences compound when
you compute Greeks, interpolate a surface, or generate trading signals.

This lecture explains the validation methodology used in Basis & Vol Lab
and summarizes the key findings. The full, runnable analysis lives in
[`notebooks/01_iv_greek_validation.ipynb`](https://github.com/vicw0ng-hk/basis-vol-lab/blob/master/notebooks/01_iv_greek_validation.ipynb).

## Methodology

### Data Source

We call Deribit's public REST endpoint
`get_book_summary_by_currency` for every active BTC option and dated
future — no API credentials required. This gives us:

- **Mark price** (coin-denominated) and **mark IV** for each option
- **Mark price** for each dated future, used as the forward price

### IV Solve

For every option with a matching forward expiry:

1. Convert the coin-denominated mark price to USD: `price_usd = mark_price × F`
2. Compute time-to-expiry `T` in year fractions
3. Solve Black-76 IV via Brent's method (`scipy.optimize.brentq`) in the
   bracket σ ∈ [0.01%, 500%]
4. Record `abs_err = |our_iv − deribit_mark_iv|`

### Error Bucketing

We slice the errors two ways:

| Dimension | Buckets |
|---|---|
| **Tenor** | 0–2d, 2–7d, 7–30d, 30–90d, 90–180d, 180–365d, 365d+ |
| **Moneyness** | deep OTM put, OTM put, near ATM put, ATM, near ATM call, OTM call, deep OTM call |

Log-moneyness `ln(K/F)` separates puts (negative) from calls (positive),
with ATM defined as |ln(K/F)| < 0.03.

## Key Findings

### IV Accuracy

- **Median absolute error** is typically below 0.001 vol points for
  liquid tenors (7–180 DTE).
- **P95 error** stays below ~0.005 vol points across the board.
- Errors concentrate in **deep-wing, short-dated options** where low
  vega amplifies any price→IV mapping noise.

### Error Patterns

- **Moneyness effect:** ATM and near-ATM options match almost exactly.
  Deep OTM options (|ln(K/F)| > 0.3) show modestly higher errors.
- **Tenor effect:** Very short-dated options (< 2 DTE) occasionally
  show larger deviations due to high gamma and sensitivity to the
  exact `asof` timestamp.
- The 2-D heatmap (moneyness × tenor) confirms that the worst-case
  corner is deep-wing + short-dated — expected and non-concerning for
  a Brent solver.

### Greek Sanity

Using our solved IV, we compute vectorized Black-76 Greeks (delta,
gamma, vega, theta) for every option in the snapshot and verify:

| Check | Expected |
|---|---|
| Call delta ∈ [0, 1] | ✓ |
| Put delta ∈ [−1, 0] | ✓ |
| Gamma ≥ 0 | ✓ |
| Vega ≥ 0 | ✓ |
| No NaN values | ✓ |

The Greek profiles show the expected shapes:

- **Delta** follows a sigmoid through moneyness, flipping sign for puts
- **Gamma** peaks ATM and decays into the wings
- **Vega** increases with √T and peaks ATM
- **Theta** is always negative (time decay)

## Running It Yourself

```bash
# CLI one-liner (text output only)
uv run python -m basis_analytics.validate --currency BTC

# Full notebook with plots
uv run --group notebooks jupyter lab notebooks/01_iv_greek_validation.ipynb
```

The notebook pulls a fresh Deribit snapshot on every run — no stored
data needed.

## Implementation

| Component | Location |
|---|---|
| IV solver | `packages/analytics/src/basis_analytics/iv.py` |
| Black-76 pricer | `packages/analytics/src/basis_analytics/pricing.py` |
| Validation logic | `packages/analytics/src/basis_analytics/validation.py` |
| CLI runner | `packages/analytics/src/basis_analytics/validate.py` |
| Greeks | `packages/analytics/src/basis_analytics/greeks.py` |
| Notebook | `notebooks/01_iv_greek_validation.ipynb` |
